# name: Gmail compose
# description: Opens a Gmail draft with the recipient, subject and text already filled in.
# permissions: open_url
# category: Productivity

TO = "friend@example.com"
SUBJECT = "Quick update"
BODY = "Hi,\n\nThis is my update for today.\n\nThanks"

def quote(text):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    out = ""
    for b in text.encode("utf-8"):
        ch = chr(b)
        out += ch if ch in safe else "%%%02X" % b
    return out


def build_url(to, subject, body):
    return ("https://mail.google.com/mail/?view=cm&fs=1&to=" + quote(to)
            + "&su=" + quote(subject) + "&body=" + quote(body))


def main():
    arise.open_url(build_url(TO, SUBJECT, BODY))
    return "Gmail draft opened - review and send"


def test_url():
    url = build_url("a@b.com", "Hi there", "x")
    assert "to=a%40b.com" in url and "su=Hi%20there" in url
