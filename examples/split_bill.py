# name: Split the bill
# description: Calculates each person's share, including a tip, and speaks it.
# permissions: speak
# category: Finance

TOTAL = 2400
PEOPLE = 4
TIP_PERCENT = 10


def share(total, people, tip_percent):
    return total * (1 + tip_percent / 100) / people


def main():
    each = share(TOTAL, PEOPLE, TIP_PERCENT)
    text = "Each of the %d people pays %.2f, including a %d percent tip." % (PEOPLE, each, TIP_PERCENT)
    arise.speak(text)
    return text


def test_share():
    assert share(1000, 4, 0) == 250
    assert round(share(1000, 4, 10), 2) == 275.0
