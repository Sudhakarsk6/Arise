# name: Countdown to a date
# description: Tells you how many days are left until an event (exam, trip, birthday).
# permissions: speak, notify
# category: Productivity

from datetime import date

EVENT_NAME = "Exam"
EVENT_DATE = "2026-12-20"      # year-month-day


def days_left(event_iso, today):
    y, m, d = [int(x) for x in event_iso.split("-")]
    return (date(y, m, d) - today).days


def message(name, left):
    if left > 1:
        return "%d days left until %s." % (left, name)
    if left == 1:
        return "Tomorrow is %s." % name
    if left == 0:
        return "Today is %s." % name
    return "%s was %d days ago." % (name, -left)


def main():
    text = message(EVENT_NAME, days_left(EVENT_DATE, date.today()))
    arise.notify("Countdown", text)
    arise.speak(text)
    return text


def test_days():
    assert days_left("2026-12-20", date(2026, 12, 10)) == 10
    assert message("Trip", 1) == "Tomorrow is Trip."
    assert message("Trip", -3) == "Trip was 3 days ago."
