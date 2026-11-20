import json, time
import pytest
from arise import location, news, weather

FORECAST = json.dumps({"current": {"temperature_2m": 31.4, "apparent_temperature": 34.2, "relative_humidity_2m": 68,
                                   "wind_speed_10m": 12.3, "weather_code": 2, "is_day": 1},
                       "daily": {"sunrise": ["2026-11-19T06:12"], "sunset": ["2026-11-19T17:41"],
                                 "uv_index_max": [6.1], "precipitation_probability_max": [20]}})
RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title> New chip   promises a full day of battery </title><link>https://example.com/a</link><pubDate>Thu, 19 Nov 2026 08:00:00 +0000</pubDate></item>
<item><title>Bad link item</title><link>http://insecure.example/b</link></item>
<item><title>Older story</title><link>https://example.com/c</link><pubDate>Wed, 18 Nov 2026 08:00:00 +0000</pubDate></item></channel></rss>"""
ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom story</title><link href="https://example.com/x"/>
<updated>2026-11-19T09:30:00Z</updated></entry></feed>"""


def test_weather_parsing_and_missing_values():
    w = weather.parse_forecast(FORECAST)
    assert w["temp"] == 31.4 and w["condition"] == "Partly cloudy" and w["sunrise"] == "06:12" and w["rain"] == 20
    sparse = weather.parse_forecast(json.dumps({"current": {"temperature_2m": 20}}))
    assert sparse["humidity"] is None and sparse["uv"] is None and weather.fmt(sparse["humidity"], unit="%") == "--"
    with pytest.raises(ValueError):
        weather.parse_forecast("{}")


def test_weather_fetch_survives_aqi_failure():
    def getter(url):
        if "air-quality" in url:
            raise OSError("down")
        return FORECAST
    w = weather.fetch(13.0, 80.2, getter)
    assert w["aqi"] is None and w["source"] == "Open-Meteo" and w["fetched_at"]
    ok = weather.fetch(13.0, 80.2, lambda u: json.dumps({"current": {"us_aqi": 87.4}}) if "air" in u else FORECAST)
    assert ok["aqi"] == 87 and weather.aqi_label(87) == "Moderate" and weather.aqi_label(None) is None


def test_news_parsing_rss_atom_and_https_only():
    items = news.parse_feed(RSS, "Src")
    assert [i["title"] for i in items] == ["New chip promises a full day of battery", "Older story"]     # http link dropped
    assert news.parse_feed(ATOM, "A")[0]["link"] == "https://example.com/x"
    with pytest.raises(Exception):
        news.parse_feed("not xml", "x")


def test_news_merge_sort_dedupe_and_errors():
    def getter(url):
        if "bad" in url:
            raise OSError("down")
        return RSS if "one" in url else ATOM
    items, errors = news.fetch_news([("One", "https://one"), ("Bad", "https://bad"), ("Two", "https://two")], 5, getter)
    assert items[0]["title"] == "New chip promises a full day of battery" or items[0]["title"] == "Atom story"
    assert len(errors) == 1 and errors[0].startswith("Bad")
    assert [i["ts"] for i in items] == sorted((i["ts"] for i in items), reverse=True)


def test_ago():
    assert news.ago(None) == "" and news.ago(1000, now=1010) == "just now"
    assert news.ago(0, now=1200) == "20 min ago" and news.ago(0, now=7300) == "2 h ago"


def test_location_fallback_and_place_name(tmp_path):
    from arise.storage import Store
    s = Store(str(tmp_path))
    assert location.current(s) is None
    s.data["location"] = {"name": "x", "lat": 13.08, "lon": 80.27}
    assert location.current(s) == (13.08, 80.27, "saved location")
    nom = json.dumps({"address": {"city": "Chennai", "state": "Tamil Nadu"}})
    assert location.place_name(13.08, 80.27, lambda u: nom) == "Chennai, Tamil Nadu"
    with pytest.raises(ValueError):
        location.place_name(0, 0, lambda u: json.dumps({"address": {}}))
