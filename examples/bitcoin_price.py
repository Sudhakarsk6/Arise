# name: Bitcoin price (voice)
# description: Speaks the current Bitcoin price (CoinGecko, free, no key).
# permissions: network, speak
# category: Finance
# NOTE: add  api.coingecko.com  to Settings > Domains scripts may call. Not investment advice.

import json

COIN = "bitcoin"
CURRENCY = "inr"
URL = "https://api.coingecko.com/api/v3/simple/price?ids=%s&vs_currencies=%s"


def fetch():
    try:
        return arise.http_get(URL % (COIN, CURRENCY))
    except (PermissionError, RuntimeError):
        return ""


def parse(raw, coin, currency):
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return data.get(coin, {}).get(currency)


def main():
    price = parse(fetch(), COIN, CURRENCY)
    if price is None:
        text = "Price unavailable. Add api.coingecko.com to Domains in Settings."
    else:
        text = "%s is %s %s right now." % (COIN.title(), format(round(price), ","), CURRENCY.upper())
    arise.speak(text)
    return text


def test_parse():
    assert parse('{"bitcoin": {"inr": 5400000}}', "bitcoin", "inr") == 5400000
    assert parse("", "bitcoin", "inr") is None
