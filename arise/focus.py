"""Focus mode: app blocking by schedule or quick session. The blocking itself is
done by the Java AccessibilityService (FocusService), which reads the same config."""
import re, time
from . import android_api as api


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def valid_time(s):
    return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s))


def is_active(store, now=None):
    f = store.data["focus"]
    now = now or time.time()
    if f.get("until_ms", 0) > now * 1000:
        return True
    if not f["enabled"]:
        return False
    lt = time.localtime(now)
    cur = lt.tm_hour * 60 + lt.tm_min
    for s in f["schedules"]:
        a, b = _mins(s["start"]), _mins(s["end"])
        if (a <= cur < b) if a <= b else (cur >= a or cur < b):
            return True
    return False


def seconds_left(store):
    return max(0, int(store.data["focus"].get("until_ms", 0) / 1000 - time.time()))


def sync(store):
    """Resolve app names to package ids so the Java service can match them."""
    pk = []
    for name in store.data["focus"]["blocked"]:
        n = name.strip().lower()
        pk.append(api.KNOWN_APPS.get(n) or (n if "." in n else None))
    store.data["focus"]["blocked_packages"] = [p for p in pk if p]
    store.save()


def start_for(store, minutes):
    store.data["focus"]["until_ms"] = int((time.time() + minutes * 60) * 1000)
    sync(store)
    store.log(f"Focus session started for {minutes} min")
    return f"Focus mode on for {minutes} minutes."


def stop(store):
    if store.data["focus"]["strict"] and is_active(store):
        return False, "Strict mode is on, so focus can't be stopped until it ends."
    store.data["focus"]["until_ms"] = 0
    store.save()
    store.log("Focus session stopped")
    return True, "Focus mode stopped."


def status_text(store):
    if not is_active(store):
        return "Focus: OFF"
    left = seconds_left(store)
    return f"Focus: ON ({left // 60} min left)" if left else "Focus: ON (scheduled)"
