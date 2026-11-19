# name: Bedtime reminder
# description: Tells you it is time to wind down. Schedule it: daily 22:30.
# permissions: notify, speak
# category: Health

MESSAGE = "It is time to wind down. Put the phone away and get ready for sleep."


def main():
    arise.notify("Bedtime", MESSAGE)
    arise.speak(MESSAGE)
    return MESSAGE


def test_message():
    assert "sleep" in MESSAGE
