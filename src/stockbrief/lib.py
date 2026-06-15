"""stockbrief.lib — deterministic portfolio math (no external deps, stdlib only).

The deterministic calculations that power a daily stock briefing live here:
average-price back-calculation, weights, overheat ratio, per-market regime,
star-rating weighted sum, retrospective return. **No judgment** — that belongs
to the consuming agent/skill. **No I/O of holdings shape opinions** — callers
pass plain dicts.

Pure stdlib so any project can `from stockbrief.lib import ...` with zero deps.
Tests: `pytest` (see tests/test_lib.py).
"""

from __future__ import annotations

import json


# ─────────────────────────────────────────────────────────────────────────────
# 공통 I/O
# ─────────────────────────────────────────────────────────────────────────────
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def holding_key(h):
    """tradable holding 의 매칭 키 — 상장지 KR은 code, US는 ticker."""
    return h.get("code") or h.get("ticker")


def avg_of(h):
    """평단 — KR은 avg_price(원), US는 avg_price_krw(원화환산)."""
    return h.get("avg_price") if h.get("avg_price") is not None else h.get("avg_price_krw")


def qty_of(h):
    return h.get("qty", 0)


# ─────────────────────────────────────────────────────────────────────────────
# 거래 체결가 복원
# ─────────────────────────────────────────────────────────────────────────────
def backcalc_buy_fill(q_before, avg_before, q_after, avg_after):
    """매수 체결가 평단 역산(정확, 평단 반올림 오차만).

    fill = (q_after*avg_after - q_before*avg_before) / (q_after - q_before)
    """
    dq = q_after - q_before
    if dq <= 0:
        raise ValueError("backcalc_buy_fill 은 수량 증가(매수)에만 쓴다")
    return (q_after * avg_after - q_before * avg_before) / dq


def classify_trade(q_before, q_after, eps=1e-9):
    """수량 변화 → 'buy' / 'sell' / 'unchanged'."""
    if q_after - q_before > eps:
        return "buy"
    if q_before - q_after > eps:
        return "sell"
    return "unchanged"


# ─────────────────────────────────────────────────────────────────────────────
# 비중 · 과열도
# ─────────────────────────────────────────────────────────────────────────────
def weights(tradable):
    """단일 비중(%) — 분모는 Σ(eval_amount) 고정.

    반환: ({key: {"name", "eval", "weight_pct"}}, total_eval)
    """
    total = sum(h.get("eval_amount", 0) for h in tradable)
    out = {}
    for h in tradable:
        e = h.get("eval_amount", 0)
        out[holding_key(h)] = {
            "name": h.get("name"),
            "eval": e,
            "weight_pct": round(100.0 * e / total, 2) if total else 0.0,
        }
    return out, total


def theme_weights(tradable, theme_map):
    """테마 비중(%) — theme_map: {테마명: [key,...]}. 분모는 전체 Σeval."""
    total = sum(h.get("eval_amount", 0) for h in tradable)
    by_key = {holding_key(h): h.get("eval_amount", 0) for h in tradable}
    out = {}
    for theme, keys in theme_map.items():
        s = sum(by_key.get(k, 0) for k in keys)
        out[theme] = round(100.0 * s / total, 2) if total else 0.0
    return out


def overheat_ratio(tradable, quotes):
    """포폴 과열도 = (RSI>70 종목 수) / (RSI 있는 종목 수). 반환 (ratio, hot, have)."""
    have = 0
    hot = 0
    for h in tradable:
        q = quotes.get(holding_key(h))
        if not q:
            continue
        rsi = q.get("rsi14")
        if rsi is None:
            continue
        have += 1
        if rsi > 70:
            hot += 1
    return (hot / have if have else 0.0), hot, have


# ─────────────────────────────────────────────────────────────────────────────
# 시장 국면
# ─────────────────────────────────────────────────────────────────────────────
def fng_band(score):
    """공포탐욕 점수(0~100) → 라벨."""
    if score <= 24:
        return "극단공포"
    if score <= 44:
        return "공포"
    if score <= 55:
        return "중립"
    if score <= 74:
        return "탐욕"
    return "극단탐욕"


# F&G 5단계 → (라벨, 톤). 공포는 '방어'가 아니라 '분할매수 기회'(역발상).
FNG_STAGE = {
    "극단공포": ("극단공포", "적극 분할매수 기회 (역사적 바닥권, 단 더 깊어질 수 있어 분할)"),
    "공포":     ("공포 우위", "분할매수 기회·경계 (공포는 도망 아닌 분할 매수)"),
    "중립":     ("중립", "평상 운영"),
    "탐욕":     ("탐욕", "추격 자제"),
    "극단탐욕": ("극단탐욕", "과열·신규 매수 자제 (버블 경계)"),
}


def computed_sentiment(rsi14, w52_pos_pct, ma_align, flow_score=None):
    """감성지수 없는 시장의 **자체 계산 프록시**(0~100, 공식 지수 아님).

    F&G 방법론(모멘텀·강도·추세·수급 정규화 합성)을 시세 지표로 차용:
      모멘텀=RSI14 · 강도=52주 위치 · 추세=ma_align→점수 · (수급=flow_score, 있으면).
    동일가중 평균. region_regime 의 sentiment_score 자리에 넣으면 그 시장도 5단계 판정.
    """
    parts = []
    if rsi14 is not None:
        parts.append(float(rsi14))
    if w52_pos_pct is not None:
        parts.append(float(w52_pos_pct))
    parts.append({"정배열": 72.0, "혼조": 50.0, "역배열": 28.0}.get(ma_align, 50.0))
    if flow_score is not None:
        parts.append(float(flow_score))
    return round(sum(parts) / len(parts), 1) if parts else None


def region_regime(sentiment_score, trend_align, trend_rate, overheat):
    """**한 시장(region)의 독립 국면**. 오버라이드 없음 — 시장마다 따로 호출.

    sentiment_score: 그 시장 감성지수(예: 미국=CNN F&G). 없으면 None → 추세만으로 판정.
    trend_align: 대표지수 ma_align('정배열'/'역배열'/'혼조'). trend_rate: 당일 등락%.
    overheat: 그 시장 보유의 과열도(0~1).
    반환: (label, detail dict[tone, fng_band|None, ...])
    """
    risk_off = trend_align == "역배열" or (trend_rate is not None and trend_rate <= -3.0)

    if sentiment_score is not None:
        band = fng_band(sentiment_score)
        label, tone = FNG_STAGE[band]
        if risk_off:
            label = "위축(방어)"
            tone = "추세 급락·위험회피 → 방어, 신규는 분할만"
            if band in ("극단공포", "공포"):
                tone += f" (F&G {band}라 우량 코어는 분할 매수 병행)"
        elif overheat >= 0.5 and (band in ("탐욕", "극단탐욕") or trend_align == "정배열"):
            label = "과열(주의)"
            tone = "탐욕+과매수 → 신규 추격 자제·분할"
        return label, {"tone": tone, "fng_band": band, "trend_align": trend_align,
                       "trend_rate": trend_rate, "overheat": round(overheat, 2), "has_sentiment": True}

    # 감성지수 없는 시장 — 추세만
    if risk_off:
        label, tone = "위축(방어)", "추세 급락/역배열 → 방어"
    elif trend_align == "정배열":
        if overheat >= 0.5:
            label, tone = "과열(주의)", "상승추세+과매수 → 추격 자제·분할"
        else:
            label, tone = "상승(우호)", "추세 우상향 → 보유·선별 매수"
    else:
        label, tone = "중립", "추세 혼조 → 평상 운영"
    return label, {"tone": tone, "fng_band": None, "trend_align": trend_align,
                   "trend_rate": trend_rate, "overheat": round(overheat, 2), "has_sentiment": False}


# ─────────────────────────────────────────────────────────────────────────────
# 별점 (가중합 + 비중적정 소점수만 기계화 / 테제·밸류·상대는 에이전트 입력)
# ─────────────────────────────────────────────────────────────────────────────
def weight_fit_score(weight_pct, high_volatility=False):
    """비중적정 소점수(0~5). ≤10→5·≤20→4·≤25→3.5·≤30→3·>30→1.5 (고변동 −0.5)."""
    if weight_pct <= 10:
        s = 5.0
    elif weight_pct <= 20:
        s = 4.0
    elif weight_pct <= 25:
        s = 3.5
    elif weight_pct <= 30:
        s = 3.0
    else:
        s = 1.5
    if high_volatility:
        s -= 0.5
    return max(0.0, s)


def round_half(x):
    """0.5 단위 반올림."""
    return round(x * 2) / 2


def star_score(thesis, value_trend, weight_fit, relative):
    """별점 = 테제0.4 + 밸류추세0.3 + 비중적정0.2 + 상대0.1, 0.5 단위 반올림."""
    raw = thesis * 0.4 + value_trend * 0.3 + weight_fit * 0.2 + relative * 0.1
    return round_half(raw)


# ─────────────────────────────────────────────────────────────────────────────
# 회고 수익률
# ─────────────────────────────────────────────────────────────────────────────
def pct_return(now_price, avg_price):
    """% 수익률 = (현재가 − 평단) / 평단 × 100."""
    return 100.0 * (now_price - avg_price) / avg_price if avg_price else 0.0


def retro_verdict(diff_pp, threshold=1.0):
    """매매후 − 단순보유 차이(%p) → 평가. ±threshold 임계."""
    if diff_pp >= threshold:
        return "🔵 매매 잘함"
    if diff_pp <= -threshold:
        return "🟢 단순 보유가 나았음"
    return "⚖️ 거의 동일"
