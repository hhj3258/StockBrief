"""시장별 국면·비중·과열도 — 결정적 계산(SDA all_regions 이식, 제네릭화).

`all_regions` 는 region 마다 `lib.region_regime` 을 독립 호출한다. 감성은 US 처럼
`cnn_fng` 소스가 있으면 그 점수, 없으면 trend_proxy 지표로 `computed_sentiment` 추정.
포맷팅(출력)은 소비자 몫 — 여기선 구조화 dict 만 돌려준다.
"""

from __future__ import annotations

from .lib import computed_sentiment, overheat_ratio, region_regime


def flow_score(investor: dict | None):
    """외국인 수급 → 0~100 (computed_sentiment 입력). 순매수=greed·연속매도=fear."""
    if not investor:
        return None
    flows = investor.get("flows") or []
    if not flows:
        return None
    f = flows[0].get("foreign_eok", 0) or 0
    streak = (investor.get("summary") or {}).get("foreign_sell_streak_days", 0) or 0
    base = 50 + (15 if f > 0 else -15 if f < 0 else 0) - min(streak, 5) * 4
    return max(0.0, min(100.0, base))


def all_regions(tradable, quotes, regions_cfg, *, cnn_score=None, investor=None):
    """시장별 독립 국면. tradable: holdings dict 리스트. quotes: {key: quote dict}.
    cnn_score: sentiment=='cnn_fng' region 에 쓸 감성 점수(없으면 None). investor: 수급 dict(선택).
    반환: {region: {flag, weight_pct, n, label, tone, detail}}.
    """
    total = sum(h.get("eval_amount", 0) for h in tradable)
    out = {}
    for region, cfg in regions_cfg.items():
        members = [h for h in tradable if h.get("region") == region]
        if not members:
            continue
        w = round(100.0 * sum(h.get("eval_amount", 0) for h in members) / total, 1) if total else 0.0
        proxy = cfg.get("trend_proxy")
        q = quotes.get(proxy, {}) if proxy else {}
        if cfg.get("sentiment") == "cnn_fng":
            s_score, s_kind = cnn_score, "CNN"
        elif proxy and (q.get("rsi14") is not None or q.get("w52_pos_pct") is not None):
            flow = flow_score(investor) if cfg.get("flow") else None
            s_score = computed_sentiment(q.get("rsi14"), q.get("w52_pos_pct"), q.get("ma_align"), flow)
            s_kind = "추정"
        else:
            s_score, s_kind = None, None
        if not proxy and s_score is None:  # global 등 — 단일 국면 N/A
            out[region] = {"flag": cfg.get("flag", ""), "weight_pct": w, "n": len(members),
                           "label": "N/A", "tone": "분산/헤지 — 단일 시장국면 해당 없음", "detail": {}}
            continue
        align = q.get("ma_align", "혼조")
        rate = q.get("rate")
        oh, _, _ = overheat_ratio(members, quotes)
        label, detail = region_regime(s_score, align, rate, oh)
        detail["sentiment_kind"], detail["sentiment_score"] = s_kind, s_score
        out[region] = {"flag": cfg.get("flag", ""), "weight_pct": w, "n": len(members),
                       "label": label, "tone": detail["tone"], "detail": detail}
    return out
