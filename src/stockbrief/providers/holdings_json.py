"""JsonHoldingsProvider — holdings.json(토스 스크린샷 스타일) 파일에서 보유 로드."""

from __future__ import annotations

from ..lib import load_json
from ..models import Holdings
from .base import HoldingsProvider


class JsonHoldingsProvider(HoldingsProvider):
    """`tradable_holdings` 배열(+선택 trades_*·현금)을 가진 JSON 파일."""

    def __init__(self, path: str):
        self.path = path

    def holdings(self) -> Holdings:
        data = load_json(self.path)
        tradable = data.get("tradable_holdings", [])
        trades = {k: v for k, v in data.items() if k.startswith("trades_")} or None
        cash = None
        ctx = data.get("context_assets") or {}
        if isinstance(ctx.get("cash"), list):
            cash = sum(c.get("amount", 0) for c in ctx["cash"]) or None
        return Holdings.from_tradable_dicts(tradable, cash=cash, trades=trades)
