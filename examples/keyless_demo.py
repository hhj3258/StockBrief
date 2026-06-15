"""키 0개 데모 — API 키 없이 보유 → 데일리 브리핑.

pip install "stockbrief[quotes-kr,quotes-us]"   # pykrx · yfinance · pandas
python examples/keyless_demo.py

보유는 합성(공개 티커 + 임의 수량) — 본인 보유로 교체해 쓰면 된다.
"""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from stockbrief.briefing import build_markdown
from stockbrief.config import AdvisorConfig
from stockbrief.pipeline import Advisor
from stockbrief.providers import (
    CnnFngProvider,
    DictHoldingsProvider,
    FreeFxProvider,
    GoogleNewsProvider,
)
from stockbrief.providers.quotes_composite import CompositeQuoteProvider
from stockbrief.providers.quotes_pykrx import PykrxQuoteProvider
from stockbrief.providers.quotes_yf import YfinanceQuoteProvider

# 합성 보유(예시) — code(KR)/ticker(US), region 은 기반시장
HOLDINGS = [
    {"code": "069500", "name": "KODEX200", "market": "KR", "region": "KR",
     "qty": 1, "avg_price": 120000, "eval_amount": 129270, "profit_pct": 7.7},
    {"ticker": "NVDA", "name": "엔비디아", "market": "US", "region": "US",
     "qty": 1, "avg_price_krw": 200000, "eval_amount": 311000, "profit_pct": 55.0},
]


def main():
    cfg = AdvisorConfig.default()   # regions·thresholds 내장 기본
    advisor = Advisor(
        cfg,
        holdings=DictHoldingsProvider(HOLDINGS),
        quotes=CompositeQuoteProvider({"KR": PykrxQuoteProvider(), "US": YfinanceQuoteProvider()}),
        fx=FreeFxProvider(),
        sentiment=CnnFngProvider(),       # 미국 F&G
        news=GoogleNewsProvider(),        # 키 불필요
    )
    inputs = advisor.run(news_days=7)
    print(build_markdown(inputs, cfg, title="키0 데모 브리핑"))


if __name__ == "__main__":
    main()
