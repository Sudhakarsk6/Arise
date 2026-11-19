# name: Telegram share
# description: Opens Telegram's share screen with your message ready - pick the chat and send.
# permissions: open_url
# category: Social

MESSAGE = "I am running late, see you soon."

def quote(text):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    out = ""
    for b in text.encode("utf-8"):
        ch = chr(b)
        out += ch if ch in safe else "%%%02X" % b
    return out


def build_url(message):
    return "https://t.me/share/url?url=%20&text=" + quote(message)


def main():
    arise.open_url(build_url(MESSAGE))
    return "Telegram opened - choose a chat and send"


def test_url():
    assert build_url("a b").endswith("text=a%20b")
