# name: Daily streak counter
# description: Run it once a day: counts your consecutive days and your best streak.
# permissions: notify, storage
# category: Health

from datetime import date, timedelta


def update(state, today_iso, yesterday_iso):
    if not state:
        return {"last": today_iso, "streak": 1, "best": 1}
    if state["last"] == today_iso:
        return state
    streak = state["streak"] + 1 if state["last"] == yesterday_iso else 1
    return {"last": today_iso, "streak": streak, "best": max(state.get("best", 0), streak)}


def main():
    today = date.today()
    state = update(arise.storage_get("streak", None), today.isoformat(), (today - timedelta(days=1)).isoformat())
    arise.storage_set("streak", state)
    text = "Streak: %d day(s). Best: %d." % (state["streak"], state["best"])
    arise.notify("Daily streak", text)
    return text


def test_update():
    s = update(None, "2026-01-01", "2025-12-31")
    s = update(s, "2026-01-02", "2026-01-01")
    assert s["streak"] == 2 and update(s, "2026-01-02", "2026-01-01") == s
    s = update(s, "2026-01-05", "2026-01-04")
    assert s["streak"] == 1 and s["best"] == 2
