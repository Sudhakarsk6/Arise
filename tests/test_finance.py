import json, pytest
from arise import finance as f
from arise.db import DB


def test_indicators():
    v = [1, 2, 3, 4, 5]
    assert f.sma(v, 3) == [None, None, 2, 3, 4]
    assert f.ema(v, 3)[2] == 2 and f.ema(v, 3)[3] == 3
    r = f.rsi(list(range(1, 40)), 14)
    assert r[-1] == 100.0 and r[5] is None
    assert f.max_drawdown([100, 120, 60, 90]) == pytest.approx(-0.5)
    assert f.volatility([100, 101]) is None


def test_backtest_no_lookahead_and_stats():
    up = [100 + i for i in range(120)]
    r = f.backtest_sma(up, 5, 20, 1000, 0)
    assert r["return"] == pytest.approx(r["buy_hold_return"], rel=0.2) and r["trades"] == 1
    zig = [100 + (10 if (i // 10) % 2 else 0) for i in range(200)]
    r2 = f.backtest_sma(zig, 3, 8)
    assert r2["trades"] >= 2 and -1 < r2["max_drawdown"] <= 0
    with pytest.raises(ValueError):
        f.backtest_sma(up, 20, 10)
    with pytest.raises(ValueError):
        f.backtest_sma([1, 2, 3], 2, 5)


def test_parsers():
    y = json.dumps({"chart": {"result": [{"timestamp": [1700000000, 1700086400],
                    "indicators": {"quote": [{"close": [10.5, None]}]}}]}})
    s, src = f.parse_yahoo(y, "X")
    assert s == [("2023-11-14", 10.5)] and "Yahoo" in src
    s, src = f.parse_stooq("Date,Open,High,Low,Close,Volume\n2026-01-02,1,2,0.5,1.5,10\n")
    assert s == [("2026-01-02", 1.5)]
    assert f.parse_csv_prices("date,close\n2026-01-01,5\nbad,row\n2026-01-02,6")[0][-1] == ("2026-01-02", 6.0)
    with pytest.raises(ValueError):
        f.parse_csv_prices("nothing")


def test_fetch_fallback_and_failure():
    def getter(url):
        if "yahoo" in url:
            raise OSError("down")
        return "Date,Open,High,Low,Close,Volume\n2026-01-02,1,2,0.5,1.5,10\n"
    q = f.fetch_daily("tcs.ns", getter)
    assert q["symbol"] == "TCS.NS" and "Stooq" in q["source"] and q["fetched_at"]
    with pytest.raises(RuntimeError):
        f.fetch_daily("x", lambda u: (_ for _ in ()).throw(OSError("down")))


def test_alerts_fire_once():
    db = DB(":memory:")
    db.x("INSERT INTO alerts(symbol,direction,price) VALUES('AAPL.US','above',100)")
    assert f.check_alerts(db, "aapl.us", 99) == []
    assert len(f.check_alerts(db, "aapl.us", 101)) == 1
    assert f.check_alerts(db, "aapl.us", 105) == []


def test_paper_trading_and_risk_limit():
    db = DB(":memory:")
    f.paper_order(db, "A", "BUY", 100, 100)               # 10,000 = 10% of equity
    assert f.paper_cash(db) == 90000
    with pytest.raises(ValueError):
        f.paper_order(db, "A", "BUY", 200, 100)           # would exceed the 20% limit
    with pytest.raises(ValueError):
        f.paper_order(db, "A", "SELL", 500, 100)
    f.paper_order(db, "A", "SELL", 40, 110)
    assert f.paper_positions(db)["A"]["qty"] == 60 and f.paper_cash(db) == 94400
    assert f.paper_equity(db, {"A": 120}) == pytest.approx(94400 + 60 * 120)
    f.paper_reset(db)
    assert f.paper_cash(db) == f.PAPER_START_CASH and not f.paper_positions(db)
