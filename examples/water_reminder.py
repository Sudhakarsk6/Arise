# name: Water reminder
# description: Counts your glasses of water today and reminds you. Schedule it: every 60 min.
# permissions: notify, storage
# category: Health

def next_state(state, today):
    if not state or state.get("day") != today:
        state = {"day": today, "count": 0}
    state["count"] += 1
    return state


def main():
    today = arise.now()[:10]
    state = next_state(arise.storage_get("water", None), today)
    arise.storage_set("water", state)
    arise.notify("Drink water", "Glass number %d today" % state["count"])
    return "Reminder %d sent" % state["count"]


def test_counts_and_resets():
    s = next_state(None, "2026-01-01")
    s = next_state(s, "2026-01-01")
    assert s["count"] == 2
    assert next_state(s, "2026-01-02")["count"] == 1
