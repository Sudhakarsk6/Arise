"""Market data (best-effort, clearly sourced), indicators, risk, backtesting and PAPER trading.
Live trading is not implemented. Nothing here is investment advice and nothing guarantees profit."""
import csv, io, json, math, time
from datetime import datetime, timezone
from .db import now
from . import net

PAPER_START_CASH = 100_000.0


# ------------------------------------------------------------------ indicators
def sma(v, n):
    return [None if i + 1 < n else sum(v[i + 1 - n:i + 1]) / n for i in range(len(v))]


def ema(v, n):
    out, k, prev = [], 2 / (n + 1), None
    for i, x in enumerate(v):
        if i + 1 < n:
            out.append(None)
        elif prev is None:
            prev = sum(v[:n]) / n
            out.append(prev)
        else:
            prev = x * k + prev * (1 - k)
            out.append(prev)
    return out


def rsi(v, n=14):
    out = [None] * len(v)
    if len(v) <= n:
        return out
    gains = [max(v[i] - v[i - 1], 0) for i in range(1, len(v))]
    losses = [max(v[i - 1] - v[i], 0) for i in range(1, len(v))]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for i in range(n, len(v)):
        if i > n:
            ag = (ag * (n - 1) + gains[i - 1]) / n
            al = (al * (n - 1) + losses[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def volatility(v):
    """Annualised standard deviation of daily returns (252 trading days)."""
    r = [v[i] / v[i - 1] - 1 for i in range(1, len(v)) if v[i - 1]]
    if len(r) < 2:
        return None
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(252)


def max_drawdown(eq):
    peak, worst = eq[0] if eq else 0, 0.0
    for x in eq:
        peak = max(peak, x)
        if peak:
            worst = min(worst, x / peak - 1)
    return worst


def backtest_sma(closes, fast=20, slow=50, cash=100_000.0, fee_pct=0.1):
    """Long-only SMA crossover. The signal uses the PREVIOUS close (no look-ahead); trades fill at the close."""
    if fast >= slow:
        raise ValueError("fast SMA must be shorter than slow SMA")
    if len(closes) < slow + 5:
        raise ValueError(f"need at least {slow + 5} prices, got {len(closes)}")
    f, s = sma(closes, fast), sma(closes, slow)
    fee, c0 = fee_pct / 100.0, cash
    qty, equity, trades, entry = 0.0, [], [], None
    for i, px in enumerate(closes):
        if i > slow:
            want = f[i - 1] > s[i - 1]
            if want and qty == 0:
                qty = cash * (1 - fee) / px
                entry, cash = px, 0.0
                trades.append(("BUY", i, px))
            elif not want and qty > 0:
                cash = qty * px * (1 - fee)
                trades.append(("SELL", i, px, px / entry - 1))
                qty = 0.0
        equity.append(cash + qty * px)
    sells = [t for t in trades if t[0] == "SELL"]
    start = slow + 1
    bh = [c0 * closes[i] / closes[start] for i in range(start, len(closes))]
    return {"equity": equity[start:], "buy_hold": bh, "return": equity[-1] / c0 - 1,
            "buy_hold_return": closes[-1] / closes[start] - 1, "max_drawdown": max_drawdown(equity[start:]),
            "trades": len(trades), "win_rate": (sum(1 for t in sells if t[3] > 0) / len(sells)) if sells else None,
            "final_equity": equity[-1]}


# ------------------------------------------------------------------ market data
def parse_yahoo(text, symbol):
    d = json.loads(text)
    res = d["chart"]["result"][0]
    ts, closes = res["timestamp"], res["indicators"]["quote"][0]["close"]
    series = [(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"), c) for t, c in zip(ts, closes) if c is not None]
    if not series:
        raise ValueError("no prices returned")
    return series, "Yahoo Finance (unofficial, may be delayed)"


def parse_stooq(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    series = [(r["Date"], float(r["Close"])) for r in rows if r.get("Close") not in (None, "", "null")]
    if not series:
        raise ValueError("no prices returned")
    return series, "Stooq (daily close)"


def parse_csv_prices(text):
    """Import your own CSV: 'date,close' per line (header optional)."""
    series = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2:
            try:
                series.append((row[0].strip(), float(row[-1] if len(row) == 2 else row[4])))
            except ValueError:
                continue
    if not series:
        raise ValueError("no valid 'date,close' rows found")
    return series, "Imported CSV"


def fetch_daily(symbol, getter=net.get_text):
    sym = symbol.strip().upper()
    errors = []
    for url, parser in ((f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=2y&interval=1d",
                         lambda t: parse_yahoo(t, sym)),
                        (f"https://stooq.com/q/d/l/?s={sym.lower()}&i=d", parse_stooq)):
        try:
            series, source = parser(getter(url))
            return {"symbol": sym, "series": series, "source": source,
                    "fetched_at": now(), "last_date": series[-1][0]}
        except Exception as e:
            errors.append(f"{type(e).__name__}")
    raise RuntimeError("no market data available (" + ", ".join(errors) + ")")


def save_quote(db, q):
    db.kv_set("quote:" + q["symbol"], json.dumps({**q, "series": q["series"][-400:]}))


def load_quote(db, symbol):
    raw = db.kv_get("quote:" + symbol.upper())
    return json.loads(raw) if raw else None


def check_alerts(db, symbol, price):
    hit = []
    for a in db.q("SELECT * FROM alerts WHERE symbol=? AND active=1", (symbol.upper(),)):
        if (a["direction"] == "above" and price >= a["price"]) or (a["direction"] == "below" and price <= a["price"]):
            hit.append(a)
            db.x("UPDATE alerts SET active=0 WHERE id=?", (a["id"],))
    return hit


# ------------------------------------------------------------------ paper trading
def paper_cash(db):
    return float(db.kv_get("paper_cash", PAPER_START_CASH))


def paper_positions(db):
    pos = {}
    for t in db.q("SELECT * FROM paper_trades ORDER BY id"):
        p = pos.setdefault(t["symbol"], {"qty": 0.0, "cost": 0.0, "last": t["price"]})
        if t["side"] == "BUY":
            p["qty"] += t["qty"]
            p["cost"] += t["qty"] * t["price"]
        else:
            avg = p["cost"] / p["qty"] if p["qty"] else 0
            p["qty"] -= t["qty"]
            p["cost"] = avg * p["qty"]
        p["last"] = t["price"]
    return {k: v for k, v in pos.items() if v["qty"] > 1e-9}


def paper_equity(db, prices=None):
    prices = prices or {}
    pos = paper_positions(db)
    return paper_cash(db) + sum(p["qty"] * prices.get(s, p["last"]) for s, p in pos.items())


def paper_order(db, symbol, side, qty, price, price_ts="", max_position_pct=20.0):
    side, symbol = side.upper(), symbol.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    qty, price = float(qty), float(price)
    if qty <= 0 or price <= 0:
        raise ValueError("quantity and price must be positive")
    cash, pos = paper_cash(db), paper_positions(db)
    if side == "BUY":
        cost = qty * price
        if cost > cash + 1e-9:
            raise ValueError("not enough paper cash")
        equity = paper_equity(db, {symbol: price})
        held = pos.get(symbol, {"qty": 0})["qty"] * price
        if (held + cost) > equity * max_position_pct / 100.0:
            raise ValueError(f"risk limit: a single position may not exceed {max_position_pct:.0f}% of equity")
        db.kv_set("paper_cash", cash - cost)
    else:
        if pos.get(symbol, {"qty": 0})["qty"] + 1e-9 < qty:
            raise ValueError("you do not hold that many")
        db.kv_set("paper_cash", cash + qty * price)
    db.x("INSERT INTO paper_trades(ts,symbol,side,qty,price,price_ts) VALUES(?,?,?,?,?,?)",
         (now(), symbol, side, qty, price, price_ts))
    db.audit("paper_trade", f"{side} {qty} {symbol} @ {price}")


def paper_reset(db):
    db.x("DELETE FROM paper_trades")
    db.kv_set("paper_cash", PAPER_START_CASH)
    db.audit("paper_reset", "")
