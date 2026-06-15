"""일봉 OHLCV → 기술적 지표 (RSI14·이동평균 정/역배열·52주 위치). pandas 필요.

어떤 QuoteProvider(pykrx·yfinance·KIS)든 일봉 DataFrame을 받으면 같은 지표를 산출하도록 공용화.
설치: `pip install "stockbrief[indicators]"` (또는 quotes-* extras 가 pandas 포함).
"""

from __future__ import annotations


def _require_pandas():
    """pandas 지연 import + 친절한 안내. 코어(dependencies=[])만 깔고 시세/지표 경로를
    쓰면 여기서 막힌다 — 어떤 extras 를 깔아야 하는지 알려준다."""
    try:
        import pandas as pd
        return pd
    except ImportError as e:  # noqa: BLE001
        raise ImportError(
            "지표 계산(indicators)에는 pandas 가 필요합니다. "
            "설치: pip install \"stockbrief[indicators]\" "
            "(또는 quotes-kr/quotes-us/kis extras — KIS 시세 경로도 pandas 필요)."
        ) from e


def _rsi14(close):
    if len(close) < 15:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    pd = _require_pandas()
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - 100 / (1 + rs)
    val = rsi.iloc[-1]
    return round(float(val), 1) if pd.notna(val) else None


def _ma(close, n):
    if len(close) < n:
        return None
    return round(float(close.tail(n).mean()), 2)


def indicators_from_ohlcv(df, price: float) -> dict:
    """일봉 DataFrame(cols: close[, high, low]) + 현재가 → 지표 dict.

    반환: {rsi14, ma{5,20,60,120}, ma_align, w52_high, w52_low, w52_pos_pct}
    """
    out: dict = {}
    if df is None or len(df) == 0 or "close" not in df.columns:
        return out
    close = df["close"].astype(float)
    out["rsi14"] = _rsi14(close)
    ma = {n: _ma(close, n) for n in (5, 20, 60, 120)}
    out["ma"] = {str(k): v for k, v in ma.items()}
    m20, m60, m120 = ma[20], ma[60], ma[120]
    if None not in (m20, m60, m120):
        if price > m20 > m60 > m120:
            out["ma_align"] = "정배열"
        elif price < m20 < m60 < m120:
            out["ma_align"] = "역배열"
        else:
            out["ma_align"] = "혼조"
    else:
        out["ma_align"] = "n/a"
    w = df.tail(252)
    hi = float(w["high"].max()) if "high" in w.columns else None
    lo = float(w["low"].min()) if "low" in w.columns else None
    out["w52_high"], out["w52_low"] = hi, lo
    if hi and lo and hi > lo:
        out["w52_pos_pct"] = round((price - lo) / (hi - lo) * 100, 1)
    return out
