# name: Daily quote (voice)
# description: Speaks and shows a different motivational line every day.
# permissions: speak, notify
# category: Productivity

from datetime import date

QUOTES = [
    "Learn from mistakes.",
    "Small steps, taken daily, build big things.",
    "Focus on progress, not perfection.",
    "Do the hard thing first.",
    "Done is better than perfect.",
    "Be kind to your future self.",
    "Calm mind, clear steps.",
    "Slow progress is still progress.",
]


def pick(day):
    return QUOTES[day.timetuple().tm_yday % len(QUOTES)]


def main():
    quote = pick(date.today())
    arise.notify("Quote of the day", quote)
    arise.speak(quote)
    return quote


def test_pick():
    assert pick(date(2026, 1, 1)) in QUOTES
    assert pick(date(2026, 1, 1)) != pick(date(2026, 1, 2))
