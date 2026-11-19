# name: Add calendar event
# description: Opens Google Calendar with an event for tomorrow 09:00-10:00 ready to save.
# permissions: open_url
# category: Productivity

from datetime import date, timedelta

TITLE = "Study session"
DETAILS = "Added by Arise"

def quote(text):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    out = ""
    for b in text.encode("utf-8"):
        ch = chr(b)
        out += ch if ch in safe else "%%%02X" % b
    return out


def stamp(day, hour):
    return day.strftime("%Y%m%d") + "T%02d0000" % hour


def build_url(title, details, day):
    return ("https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + quote(title)
            + "&details=" + quote(details) + "&dates=" + stamp(day, 9) + "/" + stamp(day, 10))


def main():
    tomorrow = date.today() + timedelta(days=1)
    arise.open_url(build_url(TITLE, DETAILS, tomorrow))
    return "Calendar opened - tap Save"


def test_url():
    d = date(2026, 11, 8)
    assert stamp(d, 9) == "20261108T090000"
    assert "dates=20261108T090000/20261108T100000" in build_url("x", "y", d)
