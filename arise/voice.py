import re, time
from . import android_api as api, automations, focus


def handle(text, store, fit=None):
    """Return the spoken answer, or None when nothing matched (-> ask the AI)."""
    t = text.lower().strip()
    store.log("voice: " + t)

    for a in store.data["automations"]:                       # your own phrases first
        if a["trigger"] == "voice" and a["value"].lower() in t:
            return automations.run_action(a["action"], a["param"], store)

    out = None
    if re.search(r"playlist|my songs|my music", t) and "play" in t:
        out = api.youtube_playlist(store.data["playlist"])
    elif (m := re.match(r"(?:search|play) (.+?) on youtube", t)) or \
         (m := re.match(r"search youtube for (.+)", t)):
        out = api.youtube_search(m.group(1))
    elif (m := re.match(r"(?:call|phone|dial) (.+)", t)):
        who = m.group(1).strip()
        number = store.data["contacts"].get(who) or (re.sub(r"[\s-]", "", who) if re.fullmatch(r"[+\d\s-]{5,}", who) else None)
        out = api.call(number) if number else f"I don't have a number for {who}. Add it in Settings."
    elif re.search(r"(stop|end|disable|turn off) focus", t):
        out = focus.stop(store)[1]
    elif re.search(r"(start|enable|turn on|begin) focus", t):
        m = re.search(r"(\d+)\s*(hour|hr|minute|min)", t)
        mins = int(m.group(1)) * (60 if m and m.group(2).startswith("h") else 1) if m else 25
        out = focus.start_for(store, mins)
    elif re.search(r"(start|begin) (a )?(workout|run|walk)", t) and fit:
        out = fit.start_workout()
    elif re.search(r"(stop|end|finish) (the |my )?(workout|run|walk)", t) and fit:
        out = fit.stop_workout()
    elif re.search(r"steps|how far|calories|distance (did|have)", t) and fit:
        out = fit.summary()
    elif (m := re.match(r"(?:open|launch|start) (.+)", t)):
        out = api.open_app(m.group(1))
    elif (m := re.match(r"(?:send|text)(?: a)?(?: message| sms)? to (\w+)(?: saying| that)? (.+)", t)):
        name, body = m.group(1), m.group(2)
        number = store.data["contacts"].get(name)
        out = api.send_sms(number, body) if number else f"I don't have a number for {name}"
    elif re.search(r"(turn on|enable|start) auto ?reply", t):
        store.data["autoreply"]["enabled"] = True
        store.save()
        out = "Auto reply is on"
    elif re.search(r"(turn off|disable|stop) auto ?reply", t):
        store.data["autoreply"]["enabled"] = False
        store.save()
        out = "Auto reply is off"
    elif "good night" in t:
        api.set_media_volume(0.0)
        out = "Good night. Media volume muted."
    elif re.search(r"what('s| is) the time|what time is it|current time", t):
        out = "It is " + time.strftime("%I:%M %p")
    if out:
        store.log("reply: " + out)
    return out
