# name: Currency rate (voice)
# description: Speaks today's exchange rate, e.g. 1 USD in INR (Frankfurter, free, no key).
# permissions: network, speak, notify
# category: Finance
# NOTE: add  api.frankfurter.app  to Settings > Domains scripts may call.

import json

BASE = "USD"
TARGET = "INR"
URL = "https://api.frankfurter.app/latest?from=%s&to=%s"


def fetch():
    try:
        return arise.http_get(URL % (BASE, TARGET))
    except (PermissionError, RuntimeError):
        return ""


def parse(raw, target):
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return data.get("rates", {}).get(target)


def main():
    rate = parse(fetch(), TARGET)
    if rate is None:
        text = "Rate unavailable. Add api.frankfurter.app to Domains in Settings."
    else:
        text = "1 %s is %.2f %s today." % (BASE, rate, TARGET)
    arise.speak(text)
    arise.notify("Currency", text)
    return text


def test_parse():
    assert parse('{"rates": {"INR": 83.5}}', "INR") == 83.5
    assert parse("", "INR") is None and parse("{}", "INR") is None
