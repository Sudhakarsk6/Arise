"""SQLite database (all personal data lives here, inside the app's private storage)."""
import os, sqlite3, threading, time

SCHEMA = """
CREATE TABLE IF NOT EXISTS automations(id INTEGER PRIMARY KEY, title TEXT, description TEXT,
  category TEXT DEFAULT 'General', icon TEXT DEFAULT 'bolt', enabled INTEGER DEFAULT 0,
  active_version_id INTEGER, schedule TEXT DEFAULT '', created_at TEXT);
CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY, automation_id INTEGER, n INTEGER, source TEXT,
  sha256 TEXT, status TEXT, permissions TEXT, report TEXT, created_at TEXT, approved_at TEXT);
CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, automation_id INTEGER, version_id INTEGER,
  started_at TEXT, ended_at TEXT, status TEXT, result TEXT, log TEXT, duration REAL);
CREATE TABLE IF NOT EXISTS habits(id INTEGER PRIMARY KEY, name TEXT, reminder TEXT DEFAULT '',
  created_at TEXT, archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS habit_logs(habit_id INTEGER, day TEXT, PRIMARY KEY(habit_id, day));
CREATE TABLE IF NOT EXISTS health(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, value REAL, unit TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS money(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, cents INTEGER, category TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS budgets(category TEXT PRIMARY KEY, limit_cents INTEGER);
CREATE TABLE IF NOT EXISTS goals(id INTEGER PRIMARY KEY, name TEXT, target_cents INTEGER,
  saved_cents INTEGER DEFAULT 0, deadline TEXT);
CREATE TABLE IF NOT EXISTS watchlist(symbol TEXT PRIMARY KEY, added_at TEXT);
CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, symbol TEXT, direction TEXT, price REAL, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS paper_trades(id INTEGER PRIMARY KEY, ts TEXT, symbol TEXT, side TEXT,
  qty REAL, price REAL, price_ts TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, ts TEXT, event TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
"""


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class DB:
    def __init__(self, path):
        self.path = path
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def x(self, sql, args=()):
        with self.lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur.lastrowid

    def audit(self, event, detail=""):
        self.x("INSERT INTO audit(ts,event,detail) VALUES(?,?,?)", (now(), event, str(detail)[:500]))

    def kv_get(self, key, default=None):
        r = self.one("SELECT value FROM kv WHERE key=?", (key,))
        return r["value"] if r else default

    def kv_set(self, key, value):
        self.x("INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (key, str(value)))

    def close(self):
        with self.lock:
            self.conn.close()
