# name: Wikipedia summary (voice)
# description: Reads the first two sentences about a topic you set (Wikipedia, free).
# permissions: network, speak
# category: General
# NOTE: add  en.wikipedia.org  to Settings > Domains scripts may call.

import json

TOPIC = "Albert Einstein"

def quote(text):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    out = ""
    for b in text.encode("utf-8"):
        ch = chr(b)
        out += ch if ch in safe else "%%%02X" % b
    return out


def fetch():
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(TOPIC.replace(" ", "_"))
    try:
        return arise.http_get(url)
    except (PermissionError, RuntimeError):
        return ""


def first_sentences(raw, count):
    try:
        text = json.loads(raw).get("extract", "")
    except (ValueError, AttributeError):
        return None
    if not text:
        return None
    return ". ".join(text.split(". ")[:count]).strip()


def main():
    text = first_sentences(fetch(), 2)
    if text is None:
        text = "No summary available. Add en.wikipedia.org to Domains in Settings."
    arise.speak(text)
    return text


def test_sentences():
    raw = json.dumps({"extract": "One. Two. Three."})
    assert first_sentences(raw, 2) == "One. Two"
    assert first_sentences("", 2) is None
