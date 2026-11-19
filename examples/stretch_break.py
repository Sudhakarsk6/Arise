# name: Stretch break reminder
# description: Sends a different stretch tip each time. Schedule it: every 45 min.
# permissions: notify
# category: Health

TIPS = [
    "Stand up and roll your shoulders 10 times.",
    "Look at something 20 feet away for 20 seconds.",
    "Stretch your neck gently left and right.",
    "Walk for two minutes and drink some water.",
    "Stretch your wrists and fingers.",
]


def tip_for(hour, minute):
    return TIPS[(hour * 60 + minute) // 45 % len(TIPS)]


def main():
    now = arise.now()
    tip = tip_for(int(now[11:13]), int(now[14:16]))
    arise.notify("Stretch break", tip)
    return tip


def test_tip():
    assert tip_for(9, 0) in TIPS and tip_for(9, 0) != tip_for(9, 45)
