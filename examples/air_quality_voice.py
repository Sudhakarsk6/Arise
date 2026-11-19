# name: Air quality (voice)
# description: Speaks the current air quality index (AQI) for your city (Open-Meteo, free).
# permissions: network, speak, notify
# category: Health
# NOTE: add  air-quality-api.open-meteo.com  to Settings > Domains scripts may call.

import json

CITY = "Chennai"
LAT = 13.08
LON = 80.27
URL = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=%s&longitude=%s&current=us_aqi"


def fetch():
    try:
        return arise.http_get(URL % (LAT, LON))
    except (PermissionError, RuntimeError):
        return ""


def level(aqi):
    if aqi <= 50:
        return "good"
    if aqi <= 100:
        return "moderate"
    if aqi <= 150:
        return "unhealthy for sensitive people"
    if aqi <= 200:
        return "unhealthy"
    if aqi <= 300:
        return "very unhealthy"
    return "hazardous"


def parse(raw):
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return data.get("current", {}).get("us_aqi")


def main():
    aqi = parse(fetch())
    if aqi is None:
        text = "Air quality unavailable. Add air-quality-api.open-meteo.com to Domains in Settings."
    else:
        text = "Air quality in %s is %s, AQI %d." % (CITY, level(aqi), round(aqi))
    arise.speak(text)
    arise.notify("Air quality", text)
    return text


def test_level():
    assert level(30) == "good" and level(120) == "unhealthy for sensitive people" and level(400) == "hazardous"
    assert parse('{"current": {"us_aqi": 77}}') == 77 and parse("") is None
