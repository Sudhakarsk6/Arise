# name: Good morning briefing
# description: Speaks a greeting, today's date and the weather. Schedule it: daily 07:30.
# permissions: network, speak
# category: Productivity
# NOTE: add  api.open-meteo.com  to Settings > Domains scripts may call.

import json
from datetime import date

LAT = 13.08
LON = 80.27
URL = "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m&timezone=auto"


def greeting(hour):
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def main():
    now = arise.now()
    hour = int(now[11:13])
    day = date.today().strftime("%A, %d %B")
    text = greeting(hour) + ". Today is " + day + "."
    try:
        temp = json.loads(arise.http_get(URL % (LAT, LON)))["current"]["temperature_2m"]
        text += " It is %d degrees outside." % round(temp)
    except (ValueError, KeyError, TypeError, PermissionError, RuntimeError):
        text += " The weather is unavailable."
    arise.speak(text)
    return text


def test_greeting():
    assert greeting(8) == "Good morning" and greeting(14) == "Good afternoon" and greeting(20) == "Good evening"
