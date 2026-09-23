"""정규화 데이터 계약 — 모든 보유 소스(스크린샷·증권사 API)를 이 형태로.

lib.py 의 결정적 함수는 plain dict(holding_key/avg_of 호환)을 받으므로,
Position/Quote 는 `.as_holding_dict()` / `.as_dict()` 로 그 dict 를 내어 다리 역할을 한다.
이렇게 하면 lib.py 는 순수(stdlib)로 남고 기존 holdings.json dict 와도 호환된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Position:
    """보유 종목 1개(정규화)."""
    key: str                       # 매칭 키 — KR=종목코드, US=티커
    name: str
    market: str                    # 상장지: "KR" | "US" (KIS 엔드포인트·FX용)
    region: str                    # 기반시장: US/KR/JP/CN/global (국면·감성용)
    qty: float
    avg_price_krw: float           # 평단(원화 기준 통일). KR=avg_price, US=환율포함 평단
    currency: str = "KRW"
    eval_amount: Optional[float] = None
    profit_pct: Optional[float] = None
    # 외화 종목 원본값(선택). 증권사 API 가 원통화로만 줄 때 채운다 — 원화 환산은 호출 측이
    # 매입 환율(avg_fx)로 다시 할 수 있게(환차손익 반영). 원화 종목은 None.
    avg_price_native: Optional[float] = None   # 주당 평단(원통화, 예: USD)
    profit_pct_native: Optional[float] = None  # 원통화 기준 수익률(환차 제외)
    fx_rate: Optional[float] = None            # avg_price_krw·eval_amount 환산에 쓴 오늘 환율

    def as_holding_dict(self) -> dict:
        """lib.py·metrics 가 기대하는 holdings.json 항목 형태."""
        d = {
            "name": self.name, "market": self.market, "region": self.region,
            "qty": self.qty, "currency": self.currency,
            "eval_amount": self.eval_amount, "profit_pct": self.profit_pct,
        }
        if self.market == "US":
            d["ticker"] = self.key
            d["avg_price_krw"] = self.avg_price_krw
            if self.avg_price_native is not None:
                d["avg_price_usd"] = self.avg_price_native
            if self.profit_pct_native is not None:
                d["profit_pct_usd"] = self.profit_pct_native
        else:
            d["code"] = self.key
            d["avg_price"] = self.avg_price_krw
        return d


@dataclass
class Holdings:
    """계좌 보유 스냅샷."""
    positions: list[Position] = field(default_factory=list)
    cash: Optional[float] = None
    trades: Optional[dict] = None   # {"trades_YYYY-MM-DD": [...]} (회고용, 있으면)

    def tradable_dicts(self) -> list[dict]:
        return [p.as_holding_dict() for p in self.positions]

    @classmethod
    def from_tradable_dicts(cls, dicts: list[dict], cash=None, trades=None) -> "Holdings":
        """holdings.json 의 tradable_holdings 배열 → Holdings."""
        pos = []
        for h in dicts:
            key = h.get("code") or h.get("ticker")
            market = h.get("market") or ("US" if h.get("ticker") else "KR")
            avg = h.get("avg_price") if h.get("avg_price") is not None else h.get("avg_price_krw")
            pos.append(Position(
                key=key, name=h.get("name", key), market=market,
                region=h.get("region") or market, qty=h.get("qty", 0),
                avg_price_krw=avg, currency=h.get("currency", "KRW"),
                eval_amount=h.get("eval_amount"), profit_pct=h.get("profit_pct"),
            ))
        return cls(positions=pos, cash=cash, trades=trades)


@dataclass
class Quote:
    """시세·지표(정규화)."""
    key: str
    name: Optional[str] = None
    price: Optional[float] = None
    prev: Optional[float] = None
    rate: Optional[float] = None          # 당일 등락 %
    rsi14: Optional[float] = None
    ma: Optional[dict] = None             # {"5":..,"20":..,"60":..,"120":..}
    ma_align: str = "n/a"                 # 정배열/역배열/혼조/n/a
    w52_high: Optional[float] = None
    w52_low: Optional[float] = None
    w52_pos_pct: Optional[float] = None

    def set_indicators(self, ind: dict) -> "Quote":
        """indicators_from_ohlcv 결과 dict → Quote 필드 대입(시세 provider 공용). self 반환."""
        self.rsi14 = ind.get("rsi14")
        self.ma = ind.get("ma")
        self.ma_align = ind.get("ma_align", "n/a")
        self.w52_high = ind.get("w52_high")
        self.w52_low = ind.get("w52_low")
        self.w52_pos_pct = ind.get("w52_pos_pct")
        return self

    def as_dict(self) -> dict:
        return {
            "code": self.key, "name": self.name, "price": self.price, "prev": self.prev,
            "rate": self.rate, "rsi14": self.rsi14, "ma": self.ma, "ma_align": self.ma_align,
            "w52_high": self.w52_high, "w52_low": self.w52_low, "w52_pos_pct": self.w52_pos_pct,
        }


@dataclass
class NewsItem:
    date: str          # YYYY-MM-DD (발행일)
    title: str
    url: str
    source: str
