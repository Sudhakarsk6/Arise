# name: Weather report (voice)
# description: Speaks the current weather for your city (Open-Meteo, free, no key).
# permissions: network, speak, notify
# category: Productivity
# NOTE: add  api.open-meteo.com  to Settings > Domains scripts may call.

import json

CITY = "Chennai"          # change to your city
LAT = 13.08               # and its latitude / longitude
LON = 80.27
URL = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
       "&current=temperature_2m,apparent_temperature,wind_speed_10m,weather_code&timezone=auto")


def describe(code):
    if code == 0:
        return "clear sky"
    if code in (1, 2, 3):
        return "partly cloudy"
    if code in (45, 48):
        return "foggy"
    if 51 <= code <= 57:
        return "drizzle"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "rain"
    if 71 <= code <= 77:
        return "snow"
    if code >= 95:
        return "a thunderstorm"
    return "unsettled weather"


def make_report(data):
    cur = data.get("current")
    if not cur or "temperature_2m" not in cur:
        return None
    return ("Weather in %s: %s, %d degrees, feels like %d, wind %d kilometres per hour."
            % (CITY, describe(cur.get("weather_code", -1)), round(cur["temperature_2m"]),
               round(cur.get("apparent_temperature", cur["temperature_2m"])), round(cur.get("wind_speed_10m", 0))))


def main():
    arise.progress(20, "asking Open-Meteo")
    blocked = False
    try:
        raw = arise.http_get(URL % (LAT, LON))
    except (PermissionError, RuntimeError):
        raw, blocked = "", True
    arise.progress(70, "reading the answer")
    try:
        data = json.loads(raw)
    except ValueError:
        data = {}
    report = make_report(data) or "The weather is unavailable right now."
    if blocked:
        report = "Weather is blocked. Add api.open-meteo.com to Domains in Settings."
    arise.speak(report)
    arise.notify("Weather", report)
    arise.progress(100, "done")
    return report


def test_describe():
    assert describe(0) == "clear sky" and describe(63) == "rain" and describe(95) == "a thunderstorm"


def test_report_handles_missing_data():
    assert make_report({}) is None


def test_report_text():
    r = make_report({"current": {"temperature_2m": 31.4, "weather_code": 1, "wind_speed_10m": 12.2}})
    assert "31 degrees" in r and "partly cloudy" in r
