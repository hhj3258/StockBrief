"""한국투자증권(KIS) 계좌 연동 — KIS 잔고로 보유를 자동 조회해 브리핑 생성.

[pykis](https://github.com/Soju06/python-kis) 세션을 받아 잔고(`account().balance()`)를
정규화 보유로 바꾼다. 시세는 키 불필요(pykrx/yfinance) 또는 별도 QuoteProvider 를 끼우면 된다.
KIS 계좌가 있는 누구나 쓸 수 있는 범용 어댑터.

    from pykis import PyKis
    from stockbrief.integrations.kis import KisHoldingsProvider, build_briefing
    kis = PyKis(...)                      # 본인 KIS 앱키/계좌
    res = build_briefing(kis, out_dir="out")   # out/briefing_YYYYMMDD.md
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from ..briefing import build_markdown
from ..config import AdvisorConfig
from ..models import Holdings, Position
from ..pipeline import Advisor
from ..providers.base import HoldingsProvider
from ..providers.fx_free import FreeFxProvider
from ..providers.news_google import GoogleNewsProvider
from ..providers.sentiment_cnn import CnnFngProvider

logger = logging.getLogger(__name__)


class KisHoldingsProvider(HoldingsProvider):
    """pykis 세션의 계좌 잔고 → 정규화 Holdings.

    country: "KR"(국내) 또는 "US"(해외). region_map: 종목→기반시장(미지정 시 country).
    ignore_symbols: 제외할 종목코드 집합(선택).
    """

    def __init__(self, session, country: str = "KR",
                 region_map: dict | None = None, ignore_symbols=None):
        self.kis = session
        self.country = country
        self.region_map = region_map or {}
        self.ignore = set(ignore_symbols or [])

    def holdings(self) -> Holdings:
        bal = self.kis.account().balance(country=self.country)
        positions = []
        for s in getattr(bal, "stocks", []):
            sym = getattr(s, "symbol", None)
            if not sym or sym in self.ignore:
                continue
            missing = [a for a in ("qty", "purchase_price", "amount", "profit_rate") if not hasattr(s, a)]
            if missing:   # pykis 필드명이 바뀌면 조용히 0 으로 채워지는 것 방지
                logger.warning("KIS 잔고 %s: 예상 필드 누락 %s → 0 으로 채움(pykis 버전 확인 필요)", sym, missing)
            positions.append(Position(
                key=sym, name=getattr(s, "name", sym), market=self.country,
                region=self.region_map.get(sym, self.country),
                qty=float(getattr(s, "qty", 0)),
                avg_price_krw=float(getattr(s, "purchase_price", 0)),
                currency="KRW",
                eval_amount=float(getattr(s, "amount", 0)),
                profit_pct=float(getattr(s, "profit_rate", 0)),
            ))
        cash = getattr(bal, "withdrawable_amount", None)
        return Holdings(positions=positions, cash=float(cash) if cash else None)


def build_briefing(
    session, *, config: AdvisorConfig | None = None, country: str = "KR",
    region_map: dict | None = None, ignore_symbols=None,
    quotes=None, sentiment=None, news=None, naver_news=None, fx=None, flow=None,
    out_dir: str | Path | None = None, date: str | None = None,
    title: str = "보유주식 데일리 브리핑",
) -> dict:
    """KIS 보유로 브리핑 마크다운 생성(+선택 파일 저장). 반환 {markdown, path?, date}.

    quotes 미지정 시 시세 단계는 graceful skip(국면은 보유만으로 제한) — 키 불필요 시세를 원하면
    CompositeQuoteProvider({"KR": PykrxQuoteProvider(), "US": YfinanceQuoteProvider()}) 를 넘긴다.
    sentiment/news/fx 는 미지정 시 키 불필요 기본(CNN·Google·ECB) 사용.
    naver_news 를 주면 한국 상장 종목 뉴스를 네이버로 조회(나머지·폴백은 news=구글).
    """
    config = config or AdvisorConfig.default()
    date = date or datetime.now().strftime("%Y-%m-%d")
    holdings = KisHoldingsProvider(session, country, region_map, ignore_symbols)
    advisor = Advisor(
        config, holdings,
        quotes=quotes,
        fx=fx or FreeFxProvider(),
        sentiment=sentiment or CnnFngProvider(),
        news=news or GoogleNewsProvider(),
        naver_news=naver_news,
        flow=flow,
    )
    md = build_markdown(advisor.run(), config, title=title, date=date)
    out = {"markdown": md, "date": date, "path": None}
    if out_dir:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"briefing_{date.replace('-', '')}.md"
        path.write_text(md, encoding="utf-8")
        out["path"] = str(path)
    return out
