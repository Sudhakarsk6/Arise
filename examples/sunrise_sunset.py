# name: Sunrise and sunset (voice)
# description: Speaks today's sunrise and sunset times for your city (Open-Meteo, free).
# permissions: network, speak
# category: General
# NOTE: add  api.open-meteo.com  to Settings > Domains scripts may call.

import json

CITY = "Chennai"
LAT = 13.08
LON = 80.27
URL = "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&daily=sunrise,sunset&timezone=auto&forecast_days=1"


def fetch():
    try:
        return arise.http_get(URL % (LAT, LON))
    except (PermissionError, RuntimeError):
        return ""


def parse(raw):
    try:
        daily = json.loads(raw).get("daily", {})
        return daily["sunrise"][0][11:16], daily["sunset"][0][11:16]
    except (ValueError, KeyError, IndexError, AttributeError, TypeError):
        return None


def main():
    times = parse(fetch())
    if times is None:
        text = "Sun times unavailable. Add api.open-meteo.com to Domains in Settings."
    else:
        text = "In %s the sun rises at %s and sets at %s." % (CITY, times[0], times[1])
    arise.speak(text)
    return text


def test_parse():
    raw = '{"daily": {"sunrise": ["2026-11-13T06:12"], "sunset": ["2026-11-13T17:41"]}}'
    assert parse(raw) == ("06:12", "17:41") and parse("") is None and parse("{}") is None
