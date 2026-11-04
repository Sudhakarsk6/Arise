"""Health, Habit and Money trackers. Missing data is reported as None (never invented)."""
import csv, io, time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from .db import now

# kind -> (unit, how to combine a day's entries)
HEALTH_KINDS = {"steps": ("steps", "sum"), "sleep": ("h", "sum"), "heart_rate": ("bpm", "avg"),
                "weight": ("kg", "last"), "activity": ("min", "sum"), "water": ("L", "sum")}
PERIOD_DAYS = {"Day": 1, "Week": 7, "Month": 30, "Year": 365}


def today_str(today=None):
    return (today or date.today()).isoformat()


# ------------------------------------------------------------------ health
def add_health(db, kind, value, source="manual", ts=None):
    if kind not in HEALTH_KINDS:
        raise ValueError("unknown measurement")
    value = float(value)
    if value < 0 or value > 1_000_000:
        raise ValueError("value out of range")
    db.x("INSERT INTO health(ts,kind,value,unit,source) VALUES(?,?,?,?,?)",
         (ts or now(), kind, value, HEALTH_KINDS[kind][0], source))


def sync_device_steps(db, steps, today=None):
    """Replace today's device-sensor step entry (the sensor reports a running total)."""
    day = today_str(today)
    db.x("DELETE FROM health WHERE kind='steps' AND source='device sensor' AND ts LIKE ?", (day + "%",))
    if steps and steps > 0:
        add_health(db, "steps", steps, "device sensor", ts=f"{day} {time.strftime('%H:%M:%S')}")


def _combine(vals, how):
    if not vals:
        return None
    return {"sum": sum(vals), "avg": sum(vals) / len(vals), "last": vals[-1]}[how]


def health_daily(db, kind, days, today=None):
    """[(YYYY-MM-DD, value or None)] oldest first."""
    end = today or date.today()
    start = end - timedelta(days=days - 1)
    rows = db.q("SELECT substr(ts,1,10) d, value FROM health WHERE kind=? AND d>=? AND d<=? ORDER BY ts",
                (kind, start.isoformat(), end.isoformat()))
    by = {}
    for r in rows:
        by.setdefault(r["d"], []).append(r["value"])
    how = HEALTH_KINDS[kind][1]
    return [((start + timedelta(days=i)).isoformat(), _combine(by.get((start + timedelta(days=i)).isoformat(), []), how))
            for i in range(days)]


def health_summary(db, kind, period, today=None):
    days = PERIOD_DAYS[period]
    unit, how = HEALTH_KINDS[kind]
    series = [v for _, v in health_daily(db, kind, days, today) if v is not None]
    if not series:
        return {"kind": kind, "unit": unit, "available": False, "days_with_data": 0}
    end = today or date.today()
    srcs = db.q("SELECT DISTINCT source FROM health WHERE kind=? AND substr(ts,1,10)>=? AND substr(ts,1,10)<=?",
                (kind, (end - timedelta(days=days - 1)).isoformat(), end.isoformat()))
    return {"kind": kind, "unit": unit, "available": True, "days_with_data": len(series),
            "total": sum(series) if how == "sum" else None, "average": sum(series) / len(series),
            "min": min(series), "max": max(series), "latest": series[-1], "how": how,
            "sources": [s["source"] for s in srcs]}


# ------------------------------------------------------------------ habits
def add_habit(db, name, reminder=""):
    name = name.strip()
    if not name:
        raise ValueError("habit name is empty")
    if reminder and not (len(reminder) == 5 and reminder[2] == ":" and reminder[:2].isdigit() and reminder[3:].isdigit()
                         and int(reminder[:2]) < 24 and int(reminder[3:]) < 60):
        raise ValueError("reminder must be HH:MM")
    return db.x("INSERT INTO habits(name,reminder,created_at) VALUES(?,?,?)", (name[:60], reminder, now()))


def set_done(db, hid, day, done=True):
    if done:
        db.x("INSERT OR IGNORE INTO habit_logs(habit_id,day) VALUES(?,?)", (hid, day))
    else:
        db.x("DELETE FROM habit_logs WHERE habit_id=? AND day=?", (hid, day))


def _days(db, hid):
    return {r["day"] for r in db.q("SELECT day FROM habit_logs WHERE habit_id=?", (hid,))}


def streaks(db, hid, today=None):
    """(current, best). The current streak stays alive if today is not done yet but yesterday was."""
    done = _days(db, hid)
    t = today or date.today()
    d = t if t.isoformat() in done else t - timedelta(days=1)
    cur = 0
    while d.isoformat() in done:
        cur += 1
        d -= timedelta(days=1)
    best, run, prev = 0, 0, None
    for s in sorted(done):
        dd = date.fromisoformat(s)
        run = run + 1 if prev and (dd - prev).days == 1 else 1
        best, prev = max(best, run), dd
    return cur, best


def completion(db, hid, days, today=None):
    done = _days(db, hid)
    t = today or date.today()
    return sum(1 for i in range(days) if (t - timedelta(days=i)).isoformat() in done) / days


def week_flags(db, hid, today=None):
    done = _days(db, hid)
    t = today or date.today()
    return [(t - timedelta(days=6 - i)).isoformat() in done for i in range(7)]


def habit_week_chart(db, today=None):
    """Daily completion % across all active habits for the last 7 days."""
    hs = db.q("SELECT id FROM habits WHERE archived=0")
    if not hs:
        return []
    t = today or date.today()
    out = []
    for i in range(6, -1, -1):
        d = (t - timedelta(days=i)).isoformat()
        n = sum(1 for h in hs if d in _days(db, h["id"]))
        out.append((d, 100.0 * n / len(hs)))
    return out


# ------------------------------------------------------------------ money (integer minor units)
def parse_amount(text):
    try:
        d = Decimal(str(text).replace(",", "").strip())
    except InvalidOperation:
        raise ValueError("amount is not a number")
    if d <= 0 or d > Decimal("1000000000"):
        raise ValueError("amount must be greater than 0")
    if d != d.quantize(Decimal("0.01")):
        raise ValueError("use at most 2 decimal places")
    return int(d * 100)


def fmt(cents, cur="INR"):
    sign = "-" if cents < 0 else ""
    return f"{sign}{cur} {abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def add_txn(db, kind, cents, category="General", note="", ts=None):
    if kind not in ("income", "expense", "saving"):
        raise ValueError("type must be income, expense or saving")
    return db.x("INSERT INTO money(ts,kind,cents,category,note) VALUES(?,?,?,?,?)",
                (ts or now(), kind, int(cents), (category or "General").strip()[:30], note.strip()[:100]))


def month_summary(db, year, month):
    ym = f"{year:04d}-{month:02d}"
    rows = db.q("SELECT kind, category, SUM(cents) c FROM money WHERE substr(ts,1,7)=? GROUP BY kind, category", (ym,))
    tot = {"income": 0, "expense": 0, "saving": 0}
    by_cat = {}
    for r in rows:
        tot[r["kind"]] += r["c"]
        if r["kind"] == "expense":
            by_cat[r["category"]] = r["c"]
    return {"month": ym, **tot, "net": tot["income"] - tot["expense"],
            "after_savings": tot["income"] - tot["expense"] - tot["saving"], "by_category": by_cat}


def cashflow_months(db, n=6, today=None):
    t = today or date.today()
    y, m, out = t.year, t.month, []
    for _ in range(n):
        s = month_summary(db, y, m)
        out.append((s["month"], s["income"], s["expense"]))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def set_budget(db, category, cents):
    db.x("INSERT INTO budgets(category,limit_cents) VALUES(?,?) ON CONFLICT(category) DO UPDATE SET limit_cents=excluded.limit_cents",
         (category.strip()[:30], int(cents)))


def budget_status(db, year, month):
    spent = month_summary(db, year, month)["by_category"]
    return [{"category": b["category"], "limit": b["limit_cents"], "spent": spent.get(b["category"], 0),
             "pct": 100.0 * spent.get(b["category"], 0) / b["limit_cents"] if b["limit_cents"] else 0.0}
            for b in db.q("SELECT * FROM budgets ORDER BY category")]


def add_goal(db, name, target_cents, deadline=""):
    return db.x("INSERT INTO goals(name,target_cents,deadline) VALUES(?,?,?)", (name.strip()[:40], int(target_cents), deadline))


def contribute_goal(db, gid, cents):
    db.x("UPDATE goals SET saved_cents=saved_cents+? WHERE id=?", (int(cents), gid))


def goals(db):
    return [{**g, "pct": min(100.0, 100.0 * g["saved_cents"] / g["target_cents"]) if g["target_cents"] else 0.0}
            for g in db.q("SELECT * FROM goals ORDER BY id")]


def export_csv(db):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["timestamp", "type", "amount", "category", "note"])
    for r in db.q("SELECT * FROM money ORDER BY ts"):
        w.writerow([r["ts"], r["kind"], f"{r['cents'] // 100}.{r['cents'] % 100:02d}", r["category"], r["note"]])
    return buf.getvalue()
