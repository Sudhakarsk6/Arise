# name: WhatsApp message
# description: Opens a WhatsApp chat with your message already typed - you just tap Send.
# permissions: open_url
# category: Social

NUMBER = "919876543210"   # country code + number, digits only (91 = India)
MESSAGE = "I am busy right now, I will call you back soon."

def quote(text):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    out = ""
    for b in text.encode("utf-8"):
        ch = chr(b)
        out += ch if ch in safe else "%%%02X" % b
    return out


def build_url(number, message):
    digits = "".join(ch for ch in number if ch.isdigit())
    return "https://wa.me/" + digits + "?text=" + quote(message)


def main():
    arise.open_url(build_url(NUMBER, MESSAGE))
    return "WhatsApp opened - tap Send"


def test_url():
    assert build_url("+91 98765-43210", "hi there") == "https://wa.me/919876543210?text=hi%20there"
