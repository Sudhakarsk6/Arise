# name: Medicine reminder
# description: Reminds you to take the medicines you list. Schedule it: daily 09:00.
# permissions: notify, speak
# category: Health
# NOTE: a simple reminder only - follow your doctor's instructions.

MEDICINES = ["Vitamin D", "Calcium"]


def make_text(items):
    return "Time to take: " + ", ".join(items) + "."


def main():
    text = make_text(MEDICINES)
    arise.notify("Medicine", text)
    arise.speak(text)
    return text


def test_text():
    assert make_text(["A", "B"]) == "Time to take: A, B."
