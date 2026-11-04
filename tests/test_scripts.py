import pytest, time
from arise.adapters import RecorderAdapter
from arise.db import DB
from arise.scripts import Scripts, TEMPLATE, is_due

GOOD = TEMPLATE
V2 = TEMPLATE.replace("1, 11", "1, 12").replace("== 55", "== 66")


@pytest.fixture()
def sc():
    ad = RecorderAdapter()
    s = Scripts(DB(":memory:"), ad)
    s.ad = ad
    return s


def test_import_creates_card_but_not_enabled(sc):
    r = sc.import_source("hello.py", GOOD)
    assert r["report"]["ok"], r["text"]
    a = sc.get(r["id"])
    assert a["title"] == "Hello Arise" and a["enabled"] == 0
    with pytest.raises(PermissionError):
        sc.run(r["id"])                       # never runs before approval


def test_bad_script_cannot_be_approved(sc):
    r = sc.import_source("bad.py", "import os\ndef main():\n    pass")
    assert not r["report"]["ok"]
    with pytest.raises(ValueError):
        sc.approve(r["id"], r["version_id"])


def test_undeclared_permission_rejected(sc):
    r = sc.import_source("x.py", "def main():\n    arise.speak('hi')\n")
    assert any("does not declare" in i for i in r["report"]["issues"])


def test_failing_test_blocks_approval(sc):
    r = sc.import_source("t.py", GOOD + "\ndef test_fail():\n    assert 1 == 2\n")
    assert not r["report"]["ok"]


def test_approve_run_history(sc):
    r = sc.import_source("hello.py", GOOD)
    sc.approve(r["id"], r["version_id"])
    prog = []
    res = sc.run(r["id"], lambda p, m: prog.append(p))
    assert res["status"] == "success" and "55" in res["text"] and prog == [20.0, 100.0]
    assert sc.last_run(r["id"])["status"] == "success"
    assert sc.ad.calls == [("notify", "Hello from Arise", "The sum of 1..10 is 55")]


def test_version_review_approve_rollback(sc):
    r = sc.import_source("hello.py", GOOD)
    sc.approve(r["id"], r["version_id"])
    n = sc.new_version(r["id"], V2)
    assert n["report"]["ok"] and "+" in n["diff"] and "-" in n["diff"]
    assert "55" in sc.run(r["id"])["text"]    # old version still active until approved
    sc.approve(r["id"], n["version_id"])
    assert "66" in sc.run(r["id"])["text"]
    sc.rollback(r["id"], r["version_id"])
    assert "55" in sc.run(r["id"])["text"]
    with pytest.raises(ValueError):
        sc.rollback(r["id"], sc.new_version(r["id"], V2)["version_id"])   # never approved


def test_tampered_source_is_blocked(sc):
    r = sc.import_source("hello.py", GOOD)
    sc.approve(r["id"], r["version_id"])
    sc.db.x("UPDATE versions SET source=? WHERE id=?", (GOOD + "\n# edited\n", r["version_id"]))
    with pytest.raises(PermissionError):
        sc.run(r["id"])
    assert any(a["event"] == "script_tamper" for a in sc.db.q("SELECT * FROM audit"))


def test_failed_run_recorded_not_crash(sc):
    src = "# name: Boom\n# permissions: notify\ndef main():\n    return 1/0\n"
    r = sc.import_source("b.py", src)
    assert not r["report"]["ok"]              # dry-run catches it before approval


def test_schedule_validation_and_due():
    now = time.mktime((2026, 11, 3, 8, 0, 0, 0, 0, -1))
    assert is_due("daily 07:30", None, now)
    assert not is_due("daily 07:30", now - 60, now)
    assert not is_due("daily 09:00", None, now)
    assert is_due("every 30 min", now - 31 * 60, now) and not is_due("every 30 min", now - 60, now)
    assert not is_due("nonsense", None, now)


def test_audit_trail(sc):
    r = sc.import_source("hello.py", GOOD); sc.approve(r["id"], r["version_id"]); sc.run(r["id"])
    ev = [a["event"] for a in sc.db.q("SELECT * FROM audit")]
    assert ev == ["script_import", "script_approve", "script_run"]
