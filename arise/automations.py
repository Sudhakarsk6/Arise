"""Trigger -> Action engine. Triggers: 'voice' (phrase) and 'time' (HH:MM).
Add new actions by adding one entry to ACTIONS."""
import time
from . import android_api as api


def _sms(p, s):
    if "|" not in p:
        return "Use the format number|text"
    number, text = p.split("|", 1)
    return api.send_sms(number.strip(), text.strip())


def _speak(p, s):
    api.speak(p)
    return p


def _quiet(p, s):
    api.set_media_volume(0)
    return "Volume muted"


ACTIONS = {
    "open_app":         lambda p, s: api.open_app(p),
    "open_url":         lambda p, s: api.open_url(p),
    "youtube_playlist": lambda p, s: api.youtube_playlist(p or s.data["playlist"]),
    "speak":            _speak,
    "send_sms":         _sms,
    "quiet_mode":       _quiet,
}

_last_run = {}


def run_action(action, param, store):
    fn = ACTIONS.get(action)
    if not fn:
        return f"Unknown action {action}"
    try:
        out = fn(param, store)
    except Exception as e:
        out = f"Action failed: {e}"
    store.log(f"action {action}({param}) -> {out}")
    return out


def check_schedule(store):
    """Call about every 20 s while the app is open."""
    now = time.strftime("%H:%M")
    today = time.strftime("%Y-%m-%d")
    for i, a in enumerate(store.data["automations"]):
        if a["trigger"] == "time" and a["value"] == now and _last_run.get(i) != (today, now):
            _last_run[i] = (today, now)
            run_action(a["action"], a["param"], store)
