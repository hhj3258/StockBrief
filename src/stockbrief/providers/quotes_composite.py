"""CompositeQuoteProvider — 상장지(market)별로 다른 QuoteProvider 로 라우팅·병합.

예(키 0개 전 시장):
    CompositeQuoteProvider({"KR": PykrxQuoteProvider(), "US": YfinanceQuoteProvider()})
"""

from __future__ import annotations

from ..models import Quote
from .base import QuoteProvider


class CompositeQuoteProvider(QuoteProvider):
    def __init__(self, by_market: dict[str, QuoteProvider], default_market: str = "KR"):
        self.by_market = by_market
        self.default_market = default_market

    def quotes(self, keys, markets=None) -> dict[str, Quote]:
        markets = markets or {}
        # market 별로 키를 모아 한 번씩 호출
        buckets: dict[str, list] = {}
        for k in keys:
            m = markets.get(k, self.default_market)
            buckets.setdefault(m, []).append(k)
        out: dict[str, Quote] = {}
        for m, ks in buckets.items():
            prov = self.by_market.get(m)
            if not prov:
                continue
            try:
                out.update(prov.quotes(ks, {k: m for k in ks}))
            except Exception:  # noqa: BLE001
                continue
        return out
