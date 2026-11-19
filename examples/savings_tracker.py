# name: Savings tracker
# description: Each run adds an amount to your saved total (remembered between runs) and speaks your progress.
# permissions: speak, storage
# category: Finance

GOAL = 50000
ADD_AMOUNT = 500


def progress(total, goal):
    return min(100, round(100 * total / goal))


def main():
    total = arise.storage_get("saved", 0) + ADD_AMOUNT
    arise.storage_set("saved", total)
    text = "You have saved %d of %d, which is %d percent of your goal." % (total, GOAL, progress(total, GOAL))
    arise.speak(text)
    return text


def test_progress():
    assert progress(500, 50000) == 1
    assert progress(60000, 50000) == 100
