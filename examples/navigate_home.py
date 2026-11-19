# name: Navigate home
# description: Opens Google Maps with directions to your home address.
# permissions: open_url
# category: General

DESTINATION = "Your home address, city"

def quote(text):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    out = ""
    for b in text.encode("utf-8"):
        ch = chr(b)
        out += ch if ch in safe else "%%%02X" % b
    return out


def build_url(destination):
    return "https://www.google.com/maps/dir/?api=1&destination=" + quote(destination)


def main():
    arise.open_url(build_url(DESTINATION))
    return "Maps opened"


def test_url():
    assert build_url("A B").endswith("destination=A%20B")
