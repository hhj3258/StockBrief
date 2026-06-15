"""AdvisorConfig — 판단 기준 + 시장 레지스트리(데이터 주도 확장 지점).

dict 또는 YAML 에서 로드. 없는 키는 내장 기본값 폴백 → 어떤 소비 프로젝트도 최소 설정으로 시작.
시장 추가 = `regions` 한 줄. 종목 테마/뉴스검색어 = `instrument_themes`/`news_queries`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# region(기반시장) 레지스트리 — sentiment 소스 키·추세 프록시 종목·수급 소스·표시 이모지.
DEFAULT_REGIONS = {
    "US": {"sentiment": "cnn_fng", "trend_proxy": "360750", "flag": "🇺🇸"},
    "KR": {"trend_proxy": "069500", "flow": "kis", "flag": "🇰🇷"},
    "JP": {"trend_proxy": "241180", "flag": "🇯🇵"},
    "CN": {"trend_proxy": "0053L0", "flag": "🇨🇳"},
    "global": {"flag": "🌐"},
}
DEFAULT_HIGH_VOL = {"우주테크", "휴머노이드", "양자컴퓨팅", "게이밍"}
DEFAULT_THRESHOLDS = {
    "target_profit_pct": 20, "stop_loss_pct": -10,
    "max_position_pct": 30, "target_cash_pct": 25, "max_theme_pct": 25,
    "rsi_overheat": 70,   # 과열 판정 RSI 임계 — 강세/약세장·성향 따라 소비자가 튜닝
}


@dataclass
class AdvisorConfig:
    regions: dict = field(default_factory=lambda: dict(DEFAULT_REGIONS))
    instrument_themes: dict = field(default_factory=dict)     # {key: 테마명}
    high_vol_themes: set = field(default_factory=lambda: set(DEFAULT_HIGH_VOL))
    news_queries: dict = field(default_factory=dict)          # {key: {primary, kr[], en[]}}
    thresholds: dict = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    benchmark: dict | None = None                             # bench_holdings/history (선택)
    default_currency: str = "KRW"

    def default_region(self, market: str) -> str:
        """region 미지정 보유의 폴백 — 상장지를 기반시장으로 간주."""
        return market

    def theme_of(self, key: str) -> str:
        return self.instrument_themes.get(key, "기타")

    def is_high_vol(self, key: str) -> bool:
        return self.theme_of(key) in self.high_vol_themes

    # ── 로더 ──
    @classmethod
    def from_dict(cls, d: dict | None) -> "AdvisorConfig":
        d = d or {}
        return cls(
            regions=d.get("regions") or dict(DEFAULT_REGIONS),
            instrument_themes=d.get("instrument_themes") or {},
            high_vol_themes=set(d.get("high_vol_themes") or DEFAULT_HIGH_VOL),
            news_queries=d.get("news_queries") or {},
            # 임계값: 내장 기본 ← 중첩 thresholds: 블록 ← 최상위 키(레거시) 순으로 덮어쓰기.
            thresholds={**DEFAULT_THRESHOLDS, **(d.get("thresholds") or {}),
                        **{k: d[k] for k in DEFAULT_THRESHOLDS if k in d}},
            benchmark=d.get("benchmark"),
            default_currency=d.get("currency", "KRW"),
        )

    @classmethod
    def from_yaml(cls, path) -> "AdvisorConfig":
        import yaml
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(yaml.safe_load(f) or {})

    @classmethod
    def default(cls) -> "AdvisorConfig":
        return cls()
