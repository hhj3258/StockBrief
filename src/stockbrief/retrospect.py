"""회고 계산 — "단순 보유 vs 실제 매매" % 수익률(결정적).

변화없음: 수익률=(현재가−평단)/평단. 추가매수: 단순=시작평단 기준·매매후=종료평단 기준.
매도: 매매후=매도가 실현·단순=안팔았으면(현재가). ±threshold%p → 평가.
모든 금액은 같은 통화로 정규화해 넣을 것(% 비교라 단위만 일치하면 됨). 행 구성은 호출 측.
"""

from __future__ import annotations

from .lib import pct_return, retro_verdict


def evaluate(row, threshold=1.0):
    """입력 행 → {name, kind, simple, traded, diff, verdict}.
    행: {name, start_qty, start_avg, end_qty, end_avg, now_price, [sold_price]}.
    """
    name = row["name"]
    sq, sa = row["start_qty"], row["start_avg"]
    eq, ea = row["end_qty"], row["end_avg"]
    now = row["now_price"]
    eps = 1e-9

    if abs(eq - sq) < eps and abs(ea - sa) < eps:        # 변화 없음
        simple = pct_return(now, sa)
        return {"name": name, "kind": "변화없음", "simple": simple,
                "traded": simple, "diff": 0.0, "verdict": "— (매매 안 함)"}

    if eq - sq > eps:                                     # 추가매수
        simple = pct_return(now, sa)
        traded = pct_return(now, ea)
        diff = traded - simple
        return {"name": name, "kind": "추가매수", "simple": simple,
                "traded": traded, "diff": diff, "verdict": retro_verdict(diff, threshold)}

    # 매도 (부분/전량)
    sold = row.get("sold_price", now)
    simple = pct_return(now, sa)
    traded = pct_return(sold, sa)
    diff = traded - simple
    return {"name": name, "kind": "매도", "simple": simple,
            "traded": traded, "diff": diff, "verdict": retro_verdict(diff, threshold)}
