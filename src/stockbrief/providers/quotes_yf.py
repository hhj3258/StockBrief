"""YfinanceQuoteProvider — 미국 상장 시세·지표, **키 불필요**. `pip install "stockbrief[quotes-us]"`."""

from __future__ import annotations

from ..indicators import indicators_from_ohlcv
from ..models import Quote
from .base import QuoteProvider


class YfinanceQuoteProvider(QuoteProvider):
    def __init__(self, period: str = "1y"):
        self.period = period

    def quotes(self, keys, markets=None) -> dict[str, Quote]:
        import yfinance as yf  # lazy
        out: dict[str, Quote] = {}
        for tkr in keys:
            if markets and markets.get(tkr) == "KR":
                continue
            try:
                df = yf.Ticker(tkr).history(period=self.period, auto_adjust=True)
            except Exception:  # noqa: BLE001
                continue
            if df is None or not len(df):
                continue
            df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                    "Close": "close", "Volume": "volume"})
            price = float(df["close"].iloc[-1])
            prev = float(df["close"].iloc[-2]) if len(df) >= 2 else None
            rate = round(100.0 * (price - prev) / prev, 2) if prev else None
            q = Quote(key=tkr, price=round(price, 2), prev=round(prev, 2) if prev else None, rate=rate)
            ind = indicators_from_ohlcv(df, price)
            q.rsi14 = ind.get("rsi14")
            q.ma = ind.get("ma")
            q.ma_align = ind.get("ma_align", "n/a")
            q.w52_high, q.w52_low, q.w52_pos_pct = ind.get("w52_high"), ind.get("w52_low"), ind.get("w52_pos_pct")
            out[tkr] = q
        return out
