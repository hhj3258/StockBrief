"""DictHoldingsProvider — 인메모리 보유 주입(증권사 API 어댑터가 만든 dict/Position 등)."""

from __future__ import annotations

from ..models import Holdings, Position
from .base import HoldingsProvider


class DictHoldingsProvider(HoldingsProvider):
    """positions: Position 리스트 또는 holdings.json 스타일 dict 리스트 모두 허용."""

    def __init__(self, positions, cash=None, trades=None):
        self._positions = positions
        self._cash = cash
        self._trades = trades

    def holdings(self) -> Holdings:
        if self._positions and isinstance(self._positions[0], Position):
            return Holdings(positions=list(self._positions), cash=self._cash, trades=self._trades)
        return Holdings.from_tradable_dicts(self._positions or [], cash=self._cash, trades=self._trades)
