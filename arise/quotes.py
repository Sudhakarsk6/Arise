import time

QUOTES = [
    "Learn from mistakes.",
    "Small steps, taken daily, build big things.",
    "Focus on progress, not perfection.",
    "Today's effort is tomorrow's ease.",
    "Start where you are. Use what you have.",
    "Quiet consistency beats loud motivation.",
    "Do the hard thing first.",
    "Rest is part of the work.",
    "Make it simple. Make it happen.",
    "Every expert was once a beginner.",
    "Be kind to your future self.",
    "Done is better than perfect.",
    "Energy goes where attention flows.",
    "Break big goals into tiny wins.",
    "Mistakes are proof you're trying.",
    "Slow progress is still progress.",
    "Choose discipline over mood.",
    "You don't need more time, just more focus.",
    "Build habits, not excuses.",
    "Calm mind, clear steps.",
]


def daily():
    return QUOTES[time.localtime().tm_yday % len(QUOTES)]


def greeting():
    h = time.localtime().tm_hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"
