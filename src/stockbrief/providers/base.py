"""Provider 인터페이스(ABC) — 모든 외부 의존을 이 뒤로.

소비 프로젝트는 필요한 provider 만 주입한다. Advisor 는 주어진 것만 쓰고 나머지는 graceful skip.
키 불필요 기본 구현은 같은 패키지에, 고정밀(KIS·네이버)은 선택 extras.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Holdings, NewsItem, Quote


class HoldingsProvider(ABC):
    """보유 종목 소스 — 유일한 필수 provider."""

    @abstractmethod
    def holdings(self) -> Holdings: ...


class QuoteProvider(ABC):
    """시세·지표 소스. markets: {key: 'KR'|'US'} 라우팅 힌트(있으면)."""

    @abstractmethod
    def quotes(self, keys: list[str], markets: dict[str, str] | None = None) -> dict[str, Quote]: ...


class FxProvider(ABC):
    @abstractmethod
    def usdkrw(self) -> float | None: ...


class SentimentProvider(ABC):
    """region 별 감성지수(0~100) 또는 None. 예: CNN F&G 는 region='US' 만 제공."""

    @abstractmethod
    def score(self, region: str) -> float | None: ...


class NewsProvider(ABC):
    @abstractmethod
    def search(self, query: str, days: int = 7, asof=None) -> list[NewsItem]: ...


class FlowProvider(ABC):
    """수급(예: 코스피 외인·기관 순매수). 반환은 investor_latest 형태 dict."""

    @abstractmethod
    def kospi_flows(self, days: int = 5) -> dict: ...
