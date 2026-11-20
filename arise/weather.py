"""Live weather from Open-Meteo (free, no key). Missing values stay None - never invented."""
import json
from datetime import datetime
from . import net

FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day"
            "&daily=sunrise,sunset,uv_index_max,precipitation_probability_max&timezone=auto&forecast_days=1")
AQI = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi"


def describe(code):
    if code is None:
        return None
    if code == 0:
        return "Clear sky"
    if code in (1, 2):
        return "Partly cloudy"
    if code == 3:
        return "Overcast"
    if code in (45, 48):
        return "Foggy"
    if 51 <= code <= 57:
        return "Drizzle"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "Rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "Snow"
    if code >= 95:
        return "Thunderstorm"
    return "Unsettled"


def aqi_label(aqi):
    if aqi is None:
        return None
    for limit, name in ((50, "Good"), (100, "Moderate"), (150, "Unhealthy for sensitive"), (200, "Unhealthy"), (300, "Very unhealthy")):
        if aqi <= limit:
            return name
    return "Hazardous"


def _first(seq):
    return seq[0] if isinstance(seq, list) and seq else None


def parse_forecast(text):
    d = json.loads(text)
    cur, daily = d.get("current") or {}, d.get("daily") or {}
    if cur.get("temperature_2m") is None:
        raise ValueError("no current weather in the response")
    hm = lambda v: v[11:16] if isinstance(v, str) and len(v) >= 16 else None
    return {"temp": cur.get("temperature_2m"), "feels": cur.get("apparent_temperature"),
            "humidity": cur.get("relative_humidity_2m"), "wind": cur.get("wind_speed_10m"),
            "code": cur.get("weather_code"), "condition": describe(cur.get("weather_code")),
            "sunrise": hm(_first(daily.get("sunrise"))), "sunset": hm(_first(daily.get("sunset"))),
            "uv": _first(daily.get("uv_index_max")), "rain": _first(daily.get("precipitation_probability_max"))}


def parse_aqi(text):
    v = (json.loads(text).get("current") or {}).get("us_aqi")
    return None if v is None else round(v)


def fetch(lat, lon, getter=net.get_text):
    w = parse_forecast(getter(FORECAST.format(lat=lat, lon=lon)))
    try:
        w["aqi"] = parse_aqi(getter(AQI.format(lat=lat, lon=lon)))
    except Exception:
        w["aqi"] = None
    w["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    w["source"] = "Open-Meteo"
    return w


def fmt(v, pattern="{:.0f}", unit=""):
    return "--" if v is None else pattern.format(v) + unit
