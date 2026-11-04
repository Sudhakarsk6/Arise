import pytest
from datetime import date
from arise import tracking as t
from arise.db import DB

T = date(2026, 11, 3)


@pytest.fixture()
def db():
    return DB(":memory:")


def test_health_unavailable_is_not_invented(db):
    s = t.health_summary(db, "heart_rate", "Week", T)
    assert s["available"] is False and "average" not in s


def test_health_aggregation_and_units(db):
    t.add_health(db, "steps", 3000, ts="2026-11-03 09:00:00")
    t.add_health(db, "steps", 2500, ts="2026-11-03 18:00:00")
    t.add_health(db, "heart_rate", 60, ts="2026-11-03 09:00:00")
    t.add_health(db, "heart_rate", 80, ts="2026-11-03 10:00:00")
    t.add_health(db, "steps", 4000, ts="2026-11-02 12:00:00")
    s = t.health_summary(db, "steps", "Week", T)
    assert s["total"] == 9500 and s["unit"] == "steps" and s["days_with_data"] == 2 and s["average"] == 4750
    assert t.health_summary(db, "heart_rate", "Day", T)["average"] == 70
    d = dict(t.health_daily(db, "steps", 7, T))
    assert d["2026-11-03"] == 5500 and d["2026-10-30"] is None
    with pytest.raises(ValueError):
        t.add_health(db, "steps", -5)


def test_device_steps_replace_not_duplicate(db):
    t.sync_device_steps(db, 1000, T); t.sync_device_steps(db, 1800, T)
    assert t.health_summary(db, "steps", "Day", T)["total"] == 1800
    assert t.health_summary(db, "steps", "Day", T)["sources"] == ["device sensor"]


def test_habit_streaks(db):
    h = t.add_habit(db, "Read")
    for d in ("2026-11-01", "2026-11-02", "2026-11-03"):
        t.set_done(db, h, d)
    assert t.streaks(db, h, T) == (3, 3)
    t.set_done(db, h, "2026-11-03", False)
    assert t.streaks(db, h, T) == (2, 2)          # alive until the day ends
    assert t.streaks(db, h, date(2026, 11, 5)) == (0, 2)
    assert t.completion(db, h, 7, T) == 2 / 7
    assert t.week_flags(db, h, T)[-3:] == [True, True, False]
    with pytest.raises(ValueError):
        t.add_habit(db, "x", "25:00")


def test_money_exact_arithmetic(db):
    assert t.parse_amount("1,234.56") == 123456
    for bad in ("abc", "0", "-5", "1.234"):
        with pytest.raises(ValueError):
            t.parse_amount(bad)
    t.add_txn(db, "income", t.parse_amount("50000"), "Salary", ts="2026-11-01 10:00:00")
    t.add_txn(db, "expense", t.parse_amount("0.10"), "Food", ts="2026-11-02 10:00:00")
    t.add_txn(db, "expense", t.parse_amount("0.20"), "Food", ts="2026-11-02 11:00:00")
    t.add_txn(db, "saving", t.parse_amount("1000"), "Goal", ts="2026-11-03 10:00:00")
    s = t.month_summary(db, 2026, 11)
    assert s["expense"] == 30 and s["net"] == 5000000 - 30 and s["after_savings"] == 5000000 - 30 - 100000
    assert t.fmt(s["net"]) == "INR 49,999.70"


def test_budget_goal_export(db):
    t.add_txn(db, "expense", 8000, "Food", ts="2026-11-02 10:00:00")
    t.set_budget(db, "Food", 10000)
    b = t.budget_status(db, 2026, 11)[0]
    assert b["spent"] == 8000 and round(b["pct"]) == 80
    g = t.add_goal(db, "Phone", 50000); t.contribute_goal(db, g, 12500)
    assert t.goals(db)[0]["pct"] == 25
    csv_text = t.export_csv(db)
    assert csv_text.splitlines()[0] == "timestamp,type,amount,category,note" and "80.00" in csv_text
    assert [m[0] for m in t.cashflow_months(db, 3, T)] == ["2026-09", "2026-10", "2026-11"]
