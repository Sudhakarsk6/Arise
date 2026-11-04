"""Automation Workspace: import, version, test, approve, run, roll back.
Nothing runs until a version is tested AND explicitly approved by the user."""
import difflib, hashlib, json, re, threading, time
from . import sandbox
from .adapters import RecorderAdapter
from .db import now
from .net import RateLimiter, get_text

CATEGORIES = ["General", "Productivity", "Health", "Finance", "Files", "Social", "Other"]
ICONS = ["bolt", "star", "bell", "file", "heart", "chart", "globe", "check", "mail"]
TEMPLATE = '''# name: Hello Arise
# description: Example script - shows a notification and returns a message.
# permissions: notify
# category: General

def main():
    arise.progress(20, "starting")
    total = sum(range(1, 11))
    arise.notify("Hello from Arise", f"The sum of 1..10 is {total}")
    arise.progress(100, "done")
    return f"Sum is {total}"


def test_sum():
    assert sum(range(1, 11)) == 55
'''


class ScriptAPI:
    """The only object a script can talk to. Every call checks the permissions you approved."""

    def __init__(self, adapter, granted, log, progress=None, kv=None, domains=(), http=get_text):
        self._adapter, self._granted, self._log = adapter, set(granted), log
        self._progress, self._kv, self._domains, self._http = progress, kv, set(domains), http

    def _need(self, perm):
        if perm not in self._granted:
            raise PermissionError(f"permission '{perm}' was not approved for this script")

    def log(self, *a):
        self._log(" ".join(str(x) for x in a))

    def progress(self, pct, msg=""):
        if self._progress:
            self._progress(max(0, min(100, float(pct))), str(msg)[:80])

    def now(self):
        return now()

    def notify(self, title, message=""):
        self._need("notify")
        return self._adapter.notify(str(title)[:80], str(message)[:300])

    def speak(self, text):
        self._need("speak")
        return self._adapter.speak(str(text)[:300])

    def open_app(self, name):
        self._need("open_app")
        return self._adapter.open_app(str(name)[:60])

    def open_url(self, url):
        self._need("open_url")
        if not re.match(r"https?://", str(url)):
            raise ValueError("only http(s) links can be opened")
        return self._adapter.open_url(str(url))

    def http_get(self, url):
        self._need("network")
        m = re.match(r"https://([^/:]+)", str(url))
        if not m or m.group(1).lower() not in self._domains:
            raise PermissionError("domain is not on your allowed-domains list (Settings)")
        return self._http(str(url))

    def storage_get(self, key, default=None):
        self._need("storage")
        return self._kv("get", str(key)[:60], default)

    def storage_set(self, key, value):
        self._need("storage")
        if len(json.dumps(value, default=str)) > 10000:
            raise ValueError("stored value too large (10 KB max)")
        self._kv("set", str(key)[:60], value)


def sha(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def is_due(schedule, last_run, now_ts):
    """schedule: 'daily HH:MM' or 'every N min'. last_run/now_ts are epoch seconds (last_run may be None)."""
    s = (schedule or "").strip().lower()
    m = re.fullmatch(r"every\s+(\d+)\s*(m|min|minutes?)", s)
    if m:
        return last_run is None or now_ts - last_run >= int(m.group(1)) * 60
    m = re.fullmatch(r"daily\s+([01]\d|2[0-3]):([0-5]\d)", s)
    if m:
        lt = time.localtime(now_ts)
        target = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(m.group(1)), int(m.group(2)), 0, 0, 0, -1))
        return now_ts >= target and (last_run is None or last_run < target)
    return False


class Scripts:
    def __init__(self, db, adapter, domains_getter=lambda: (), progress_default=None):
        self.db, self.adapter, self.domains = db, adapter, domains_getter
        self.limiter = RateLimiter(10, 60)
        self.running = set()

    # ------------------------------------------------------------ analysis
    def analyse(self, source, fallback="script"):
        issues, used, _ = sandbox.check_policy(source)
        meta = sandbox.parse_meta(source, fallback)
        declared = set(meta["permissions"])
        for p in sorted(declared - sandbox.PERMISSIONS):
            issues.append(f"unknown permission '{p}' (allowed: {', '.join(sorted(sandbox.PERMISSIONS))})")
        for p in sorted(used - declared):
            issues.append(f"script uses '{p}' but does not declare it in '# permissions:'")
        tests = [] if issues else sandbox.run_tests(source, self._dry_api(declared))
        ok = not issues and all(t["ok"] for t in tests)
        return {"ok": ok, "issues": issues, "tests": tests, "meta": meta, "permissions": sorted(declared)}

    def _dry_api(self, perms):
        def factory():
            return ScriptAPI(RecorderAdapter(), perms, lambda m: None, kv=lambda *a: a[-1],
                             domains=(), http=lambda u: "")
        return factory

    @staticmethod
    def format_report(rep):
        lines = []
        for i in rep["issues"]:
            lines.append("[x] " + i)
        for t in rep["tests"]:
            lines.append(("[ok] " if t["ok"] else "[x] ") + f"{t['name']}: {t['message']}")
        lines.append("RESULT: " + ("all checks passed" if rep["ok"] else "FAILED - fix the problems above"))
        return "\n".join(lines)

    # ------------------------------------------------------------ lifecycle
    def import_source(self, filename, source):
        name = re.sub(r"\.py$", "", filename.replace("\\", "/").split("/")[-1]) or "script"
        rep = self.analyse(source, name)
        m = rep["meta"]
        aid = self.db.x("INSERT INTO automations(title,description,category,icon,enabled,created_at) VALUES(?,?,?,?,0,?)",
                        (m["name"], m["description"], m["category"] if m["category"] in CATEGORIES else "General",
                         "bolt", now()))
        vid = self._add_version(aid, source, rep)
        self.db.audit("script_import", f"{m['name']} v1 ok={rep['ok']}")
        return {"id": aid, "version_id": vid, "report": rep, "text": self.format_report(rep)}

    def new_version(self, aid, source):
        a = self.get(aid)
        rep = self.analyse(source, a["title"])
        vid = self._add_version(aid, source, rep)
        self.db.audit("script_version", f"{a['title']} ok={rep['ok']}")
        return {"version_id": vid, "report": rep, "text": self.format_report(rep), "diff": self.diff(aid, vid)}

    def _add_version(self, aid, source, rep):
        n = (self.db.one("SELECT MAX(n) m FROM versions WHERE automation_id=?", (aid,))["m"] or 0) + 1
        return self.db.x("INSERT INTO versions(automation_id,n,source,sha256,status,permissions,report,created_at) "
                         "VALUES(?,?,?,?,?,?,?,?)",
                         (aid, n, source, sha(source), "tested" if rep["ok"] else "failed",
                          json.dumps(rep["permissions"]), self.format_report(rep), now()))

    def approve(self, aid, vid):
        v = self.version(vid)
        if not v or v["automation_id"] != aid:
            raise ValueError("version not found")
        if v["status"] not in ("tested", "approved"):
            raise ValueError("this version has not passed its checks and cannot be approved")
        if sha(v["source"]) != v["sha256"]:
            raise ValueError("stored source does not match its hash")
        self.db.x("UPDATE versions SET status='approved', approved_at=? WHERE id=?", (now(), vid))
        meta = sandbox.parse_meta(v["source"])
        self.db.x("UPDATE automations SET active_version_id=?, enabled=1, description=CASE WHEN description='' "
                  "THEN ? ELSE description END WHERE id=?", (vid, meta["description"], aid))
        self.db.audit("script_approve", f"automation {aid} version {v['n']} perms={v['permissions']}")

    def rollback(self, aid, vid):
        v = self.version(vid)
        if not v or v["automation_id"] != aid or not v["approved_at"]:
            raise ValueError("can only roll back to a previously approved version")
        self.db.x("UPDATE automations SET active_version_id=?, enabled=1 WHERE id=?", (vid, aid))
        self.db.audit("script_rollback", f"automation {aid} -> version {v['n']}")

    def set_enabled(self, aid, enabled):
        a = self.get(aid)
        if enabled and not a["active_version_id"]:
            raise ValueError("approve a version first")
        self.db.x("UPDATE automations SET enabled=? WHERE id=?", (1 if enabled else 0, aid))
        self.db.audit("script_enable" if enabled else "script_disable", a["title"])

    def update_meta(self, aid, title, description, category, icon, schedule):
        if schedule and not (re.fullmatch(r"every\s+\d+\s*(m|min|minutes?)", schedule.lower())
                             or re.fullmatch(r"daily\s+([01]\d|2[0-3]):[0-5]\d", schedule.lower())):
            raise ValueError("schedule must look like 'daily 07:30' or 'every 30 min'")
        self.db.x("UPDATE automations SET title=?,description=?,category=?,icon=?,schedule=? WHERE id=?",
                  (title.strip()[:60] or "Untitled", description.strip()[:200], category, icon, schedule.strip().lower(), aid))

    def delete(self, aid):
        a = self.get(aid)
        for t in ("versions", "runs"):
            self.db.x(f"DELETE FROM {t} WHERE automation_id=?", (aid,))
        self.db.x("DELETE FROM automations WHERE id=?", (aid,))
        self.db.audit("script_delete", a["title"])

    # ------------------------------------------------------------ queries
    def list(self):
        return self.db.q("SELECT a.*, v.n AS active_n FROM automations a LEFT JOIN versions v "
                         "ON v.id=a.active_version_id ORDER BY a.id")

    def get(self, aid):
        a = self.db.one("SELECT * FROM automations WHERE id=?", (aid,))
        if not a:
            raise KeyError("automation not found")
        return a

    def version(self, vid):
        return self.db.one("SELECT * FROM versions WHERE id=?", (vid,))

    def versions(self, aid):
        return self.db.q("SELECT id,n,status,sha256,permissions,created_at,approved_at FROM versions "
                         "WHERE automation_id=? ORDER BY n DESC", (aid,))

    def latest_version(self, aid):
        return self.db.one("SELECT * FROM versions WHERE automation_id=? ORDER BY n DESC LIMIT 1", (aid,))

    def history(self, aid, n=10):
        return self.db.q("SELECT * FROM runs WHERE automation_id=? ORDER BY id DESC LIMIT ?", (aid, n))

    def last_run(self, aid):
        h = self.history(aid, 1)
        return h[0] if h else None

    def diff(self, aid, vid):
        v = self.version(vid)
        a = self.get(aid)
        base = self.version(a["active_version_id"]) if a["active_version_id"] else None
        if base is None or base["id"] == vid:
            prev = self.db.one("SELECT source FROM versions WHERE automation_id=? AND n<? ORDER BY n DESC LIMIT 1",
                               (aid, v["n"]))
            base = prev
        old = (base["source"] if base else "").splitlines()
        return "\n".join(difflib.unified_diff(old, v["source"].splitlines(), "previous", f"v{v['n']}", lineterm="", n=2)) \
            or "(no changes)"

    # ------------------------------------------------------------ run
    def run(self, aid, progress=None):
        a = self.get(aid)
        if not a["enabled"] or not a["active_version_id"]:
            raise PermissionError("this automation is not approved/enabled")
        if aid in self.running:
            raise RuntimeError("already running")
        if not self.limiter.allow(str(aid)):
            raise RuntimeError("too many runs - wait a minute")
        v = self.version(a["active_version_id"])
        if sha(v["source"]) != v["sha256"]:
            self.db.audit("script_tamper", f"automation {aid} hash mismatch - blocked")
            raise PermissionError("script failed its integrity check - blocked")
        perms = json.loads(v["permissions"] or "[]")
        rid = self.db.x("INSERT INTO runs(automation_id,version_id,started_at,status) VALUES(?,?,?,'running')",
                        (aid, v["id"], now()))
        self.running.add(aid)
        logs = []

        def kv(op, key, val=None):
            k = f"script:{aid}:{key}"
            if op == "set":
                self.db.kv_set(k, json.dumps(val, default=str))
                return None
            raw = self.db.kv_get(k)
            return json.loads(raw) if raw is not None else val

        api = ScriptAPI(self.adapter, perms, logs.append, progress, kv, self.domains())
        try:
            r = sandbox.execute(v["source"], api)
        finally:
            self.running.discard(aid)
        status = "success" if r["ok"] else "failed"
        text = r.get("result") if r["ok"] else r.get("error")
        self.db.x("UPDATE runs SET ended_at=?,status=?,result=?,log=?,duration=? WHERE id=?",
                  (now(), status, str(text)[:2000], "\n".join(filter(None, [r.get("log", ""), *logs]))[:5000],
                   r.get("duration", 0), rid))
        self.db.audit("script_run", f"{a['title']} -> {status}")
        return {"status": status, "text": text, "duration": r.get("duration", 0), "run_id": rid}

    def run_async(self, aid, progress, done):
        def job():
            try:
                res = self.run(aid, progress)
            except Exception as e:
                res = {"status": "failed", "text": str(e), "duration": 0}
            done(res)
        threading.Thread(target=job, daemon=True).start()

    def due(self, now_ts=None):
        now_ts = now_ts or time.time()
        out = []
        for a in self.list():
            if a["enabled"] and a["schedule"]:
                last = self.last_run(a["id"])
                lt = time.mktime(time.strptime(last["started_at"], "%Y-%m-%d %H:%M:%S")) if last else None
                if is_due(a["schedule"], lt, now_ts):
                    out.append(a["id"])
        return out
