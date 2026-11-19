# name: Google search
# description: Opens a Google search for the words you set.
# permissions: open_url
# category: General

QUERY = "best study music"

def quote(text):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    out = ""
    for b in text.encode("utf-8"):
        ch = chr(b)
        out += ch if ch in safe else "%%%02X" % b
    return out


def build_url(query):
    return "https://www.google.com/search?q=" + quote(query)


def main():
    arise.open_url(build_url(QUERY))
    return "Searching for " + QUERY


def test_url():
    assert build_url("a b").endswith("q=a%20b")
