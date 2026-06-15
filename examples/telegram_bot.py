"""예시: 키리스 브리핑 → 텔레그램 전송 (서버 없이 봇 구축).

전제: pip install "stockbrief[quotes-kr,quotes-us]"  +  텔레그램 봇.
환경변수 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 필요 (토큰은 코드에 하드코딩 금지).
보유는 합성 예시 — 실제로는 JsonHoldingsProvider("holdings.json") 등으로 교체하세요.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def send_telegram(text: str) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat, "text": text, "parse_mode": "Markdown"}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=15) as r:
        return json.load(r)


def main():
    from stockbrief.briefing import build_markdown
    from stockbrief.config import AdvisorConfig
    from stockbrief.pipeline import Advisor
    from stockbrief.providers import (CnnFngProvider, DictHoldingsProvider,
                                      FreeFxProvider, GoogleNewsProvider)
    from stockbrief.providers.quotes_composite import CompositeQuoteProvider
    from stockbrief.providers.quotes_pykrx import PykrxQuoteProvider
    from stockbrief.providers.quotes_yf import YfinanceQuoteProvider

    advisor = Advisor(
        AdvisorConfig.default(),
        holdings=DictHoldingsProvider([
            {"code": "069500", "name": "KODEX200", "market": "KR", "region": "KR",
             "qty": 1, "avg_price": 120000, "eval_amount": 129270},
            {"ticker": "NVDA", "name": "엔비디아", "market": "US", "region": "US",
             "qty": 1, "avg_price_krw": 200000, "eval_amount": 311000},
        ]),
        quotes=CompositeQuoteProvider({"KR": PykrxQuoteProvider(), "US": YfinanceQuoteProvider()}),
        fx=FreeFxProvider(), sentiment=CnnFngProvider(), news=GoogleNewsProvider(),
    )
    md = build_markdown(advisor.run(), advisor.config, title="데일리 브리핑")
    print(md[:500])
    res = send_telegram(md)
    print("텔레그램 전송:", res.get("ok"))


if __name__ == "__main__":
    main()
