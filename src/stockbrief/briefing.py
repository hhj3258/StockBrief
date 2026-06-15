"""build_markdown — BriefingInputs → 데일리 브리핑 마크다운(결정적 부분).

시장별 국면·보유 종목 표·뉴스·요약을 마크다운으로. **별점·매수/매도/유지 판단은 여기 없다** —
그건 포터블 스킬(에이전트) 또는 소비자 LLM 이 이 마크다운/데이터를 받아 덧붙인다.
대시보드는 이 마크다운을 그대로 렌더해도 되고, LLM 산문을 얹어도 된다.
"""

from __future__ import annotations


def _region_meta(detail: dict) -> str:
    kind = detail.get("sentiment_kind")
    if kind == "CNN":
        return f"F&G {detail.get('fng_band')}({detail.get('sentiment_score')})"
    if kind == "추정":
        return f"추정감성 {detail.get('sentiment_score')}({detail.get('fng_band')})"
    return "추세만(감성 N/A)"


def build_markdown(inputs, config, *, title: str = "포트폴리오 데일리 브리핑", date: str = "") -> str:
    L = []
    head = f"# {title}" + (f" — {date}" if date else "")
    L.append(head)
    oh_ratio, hot, have = inputs.overheat
    L.append(f"> Σ평가 {round(inputs.total_eval):,} · 과열도 {hot}/{have}"
             + (f" · 환율 {inputs.fx}" if inputs.fx else ""))

    # 시장별 국면
    L.append("\n## 🌡️ 시장 국면 (시장별 독립)")
    for region, r in sorted(inputs.regions.items(), key=lambda x: -x[1]["weight_pct"]):
        d = r.get("detail", {})
        rate = d.get("trend_rate")
        rate_s = f" {rate:+.2f}%" if rate is not None else ""
        align = d.get("trend_align", "n/a") or "n/a"
        meta = _region_meta(d) if d else "—"
        L.append(f"- {r['flag']} **{region}** ({r['weight_pct']}%, {r['n']}종목): "
                 f"{r['label']} — {meta} · 추세 {align}{rate_s} · {r['tone']}")

    # 보유 종목
    L.append("\n## 📊 보유 종목")
    L.append("| 종목 | 시장 | 비중 | 손익 | 현재가 | RSI · 추세 |")
    L.append("|---|---|---:|---:|---:|---|")
    for p in sorted(inputs.holdings.positions,
                    key=lambda p: -(inputs.weights.get(p.key, {}).get("weight_pct") or 0)):
        q = inputs.quotes.get(p.key, {})
        w = inputs.weights.get(p.key, {}).get("weight_pct")
        pnl = f"{p.profit_pct:+.1f}%" if p.profit_pct is not None else "—"
        price = q.get("price")
        price_s = f"{price:,}" if isinstance(price, (int, float)) else "—"
        rsi = q.get("rsi14")
        align = q.get("ma_align", "")
        rt = f"{rsi}·{align}" if rsi is not None else (align or "—")
        L.append(f"| {p.name} | {p.region} | {w}% | {pnl} | {price_s} | {rt} |")

    # 뉴스
    if any(inputs.news.values()):
        L.append("\n## 📰 종목 뉴스 (발행 7일 내)")
        bykey = {p.key: p.name for p in inputs.holdings.positions}
        for key, items in inputs.news.items():
            if not items:
                continue
            L.append(f"- **{bykey.get(key, key)}**")
            for it in items[:3]:
                L.append(f"  - [{it.date}] [{it.title}]({it.url}) ({it.source})")

    L.append("\n---\n> 별점·매수/매도/유지 판단은 스킬/LLM 이 위 데이터를 근거로 덧붙입니다. (정보 제공용)")
    return "\n".join(L)
