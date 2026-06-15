"""stockbrief.lib 결정적 산수 단위테스트 (SDA portfolio_lib selftest 이관)."""

from stockbrief.lib import (
    backcalc_buy_fill,
    classify_trade,
    computed_sentiment,
    fng_band,
    pct_return,
    portfolio_concentration,
    region_regime,
    region_weights,
    retro_verdict,
    star_breakdown,
    star_score,
    weight_fit_score,
)


def test_backcalc_buy_fill():
    fill = backcalc_buy_fill(10.327575, 211898, 11.421258, 222593)
    assert 323000 < fill < 324000


def test_classify_trade():
    assert classify_trade(186, 136) == "sell"
    assert classify_trade(10.33, 11.42) == "buy"
    assert classify_trade(67, 67) == "unchanged"


def test_fng_band():
    assert fng_band(27.5) == "공포"
    assert fng_band(67) == "탐욕"
    assert fng_band(10) == "극단공포"


def test_region_regime_with_sentiment():
    assert region_regime(27.5, "혼조", -2.4, 0.0)[0] == "공포 우위"
    assert region_regime(15, "혼조", -1.0, 0.0)[0] == "극단공포"
    assert region_regime(27.5, "역배열", -1.0, 0.0)[0] == "위축(방어)"   # 역배열 → 방어
    assert region_regime(27.5, "혼조", -5.0, 0.0)[0] == "위축(방어)"     # -5% 급락 → 방어
    assert region_regime(60, "정배열", 1.0, 0.6)[0] == "과열(주의)"      # 탐욕+과매수
    assert region_regime(60, "혼조", 1.0, 0.1)[0] == "탐욕"
    assert region_regime(80, "혼조", 0.0, 0.1)[0] == "극단탐욕"


def test_region_regime_trend_only():
    assert region_regime(None, "정배열", 1.0, 0.1)[0] == "상승(우호)"
    assert region_regime(None, "역배열", -1.0, 0.0)[0] == "위축(방어)"
    assert region_regime(None, "혼조", 0.0, 0.0)[0] == "중립"
    assert region_regime(None, "정배열", 1.0, 0.6)[0] == "과열(주의)"


def test_computed_sentiment():
    assert computed_sentiment(50, 80, "정배열") == round((50 + 80 + 72) / 3, 1)
    assert computed_sentiment(30, 20, "역배열") == round((30 + 20 + 28) / 3, 1)
    assert computed_sentiment(60, 60, "혼조", flow_score=70) == round((60 + 60 + 50 + 70) / 4, 1)


def test_weight_fit_and_star():
    assert weight_fit_score(9) == 5.0
    assert weight_fit_score(18) == 4.0
    assert weight_fit_score(22) == 3.5
    assert weight_fit_score(1.1, high_volatility=True) == 4.5
    assert star_score(4.5, 4.5, 3.5, 3.5) == 4.0


def test_retrospect():
    assert abs(pct_return(44390, 30975) - 43.31) < 0.1
    assert retro_verdict(-15.4) == "🟢 단순 보유가 나았음"
    assert retro_verdict(0.3) == "⚖️ 거의 동일"
    assert retro_verdict(2.0) == "🔵 매매 잘함"


def test_star_breakdown():
    b = star_breakdown(4.5, 4.5, 3.5, 3.5)
    assert b["stars"] == star_score(4.5, 4.5, 3.5, 3.5)          # 최종 별점은 star_score 와 동일
    assert b["components"]["thesis"]["contribution"] == round(4.5 * 0.4, 3)
    assert b["components"]["relative"]["weight"] == 0.1
    # 기여도 합 = raw_total
    assert abs(sum(c["contribution"] for c in b["components"].values()) - b["raw_total"]) < 1e-9


def test_region_weights_and_concentration():
    tradable = [
        {"code": "069500", "name": "코어", "region": "KR", "eval_amount": 100},
        {"ticker": "NVDA", "name": "엔비디아", "region": "US", "eval_amount": 300},
    ]
    rw = region_weights(tradable)
    assert rw["US"] == 75.0 and rw["KR"] == 25.0
    con = portfolio_concentration(tradable, theme_map={"AI": ["NVDA"]}, max_region_pct=70.0)
    assert con["single"]["NVDA"] == 75.0
    assert con["themes"]["AI"] == 75.0
    assert any("시장 집중: US" in f for f in con["flags"])       # US 75% > 70% → 경고
