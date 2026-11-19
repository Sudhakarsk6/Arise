# name: Birthday check
# description: Reminds you of birthdays that fall today. Schedule it: daily 08:00.
# permissions: notify, speak
# category: Social

PEOPLE = [
    ("Amma", "05-14"),
    ("Friend", "11-13"),
]


def today_names(people, month_day):
    return [name for name, md in people if md == month_day]


def main():
    names = today_names(PEOPLE, arise.now()[5:10])
    if not names:
        return "No birthdays today"
    text = "Today is the birthday of " + " and ".join(names) + ". Send your wishes!"
    arise.notify("Birthday", text)
    arise.speak(text)
    return text


def test_names():
    assert today_names(PEOPLE, "05-14") == ["Amma"]
    assert today_names(PEOPLE, "01-01") == []
