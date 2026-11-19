# name: YouTube search
# description: Searches YouTube for the words in QUERY (change them) and speaks a confirmation.
# permissions: open_url, speak
# category: General

QUERY = "relaxing music"


def build_url(query):
    words = query.strip().split()
    return "https://www.youtube.com/results?search_query=" + "+".join(words)


def main():
    arise.open_url(build_url(QUERY))
    arise.speak("Searching YouTube for " + QUERY)
    return "Searched for " + QUERY


def test_url():
    assert build_url("a b") == "https://www.youtube.com/results?search_query=a+b"
