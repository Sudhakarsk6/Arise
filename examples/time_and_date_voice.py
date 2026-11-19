# name: Time and date (voice)
# description: Speaks the current time and today's date.
# permissions: speak
# category: General

from datetime import date


def make_text(now, today):
    hour, minute = int(now[11:13]), int(now[14:16])
    suffix = "AM" if hour < 12 else "PM"
    return "It is %d:%02d %s on %s." % (hour % 12 or 12, minute, suffix, today.strftime("%A, %d %B %Y"))


def main():
    text = make_text(arise.now(), date.today())
    arise.speak(text)
    return text


def test_text():
    assert make_text("2026-11-13 14:05:00", date(2026, 11, 13)) == "It is 2:05 PM on Friday, 13 November 2026."
