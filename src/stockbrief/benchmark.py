"""벤치마크 점수판 계산 primitive — 내 포폴 평가액·환율 해석(결정적).

IO·history 기록은 소비자 몫(각자 benchmark 상태 파일을 가짐). 여기선 값 계산만.
my_value 는 **라이브 시세로 재계산**(벤치가 라이브라 apples-to-apples) — US 종목은 ×fx 환산,
시세/환율 없으면 그 종목만 eval_amount 폴백.
"""

from __future__ import annotations


def resolve_fx(arg_fx, quotes):
    """--fx 우선, 없으면 quotes 의 _fx(kis_quote 등이 자동수집한 USD/KRW)."""
    if arg_fx is not None:
        return arg_fx
    return (quotes.get("_fx") or {}).get("USDKRW")


def my_value(holdings, quotes=None, fx=None):
    """내 포폴 평가액. quotes 주면 라이브 재계산, 없으면 eval_amount 합(스냅샷)."""
    tradable = holdings["tradable_holdings"]
    if quotes is None:
        return sum(h.get("eval_amount", 0) for h in tradable)
    total = 0.0
    for h in tradable:
        q = quotes.get(h.get("code") or h.get("ticker"))
        if not q or q.get("price") is None:
            total += h.get("eval_amount", 0)
            continue
        if h.get("market") == "US":      # USD 시세 → 원화 환산
            if fx is None:
                total += h.get("eval_amount", 0)   # FX 없으면 그 종목만 stale 폴백
            else:
                total += h["qty"] * q["price"] * fx
        else:                            # KRW 시세 그대로
            total += h["qty"] * q["price"]
    return total


def excess_pct(my, bench):
    """초과수익(%p) = my/bench − 1."""
    return round(100.0 * (my / bench - 1), 1) if bench else 0.0
