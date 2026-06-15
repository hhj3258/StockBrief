"""한국투자증권(KIS) 계좌 보유 → 브리핑 (범용 예시).

전제: pip install "stockbrief[kis,quotes-kr,quotes-us]"  +  본인 KIS 앱키/계좌.
pykis 세션 생성은 https://github.com/Soju06/python-kis 참고. (키는 코드에 하드코딩하지 말 것)
"""

from __future__ import annotations

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    from pykis import PyKis  # 선택 의존성

    # 자격증명은 환경변수/안전한 저장소에서 (리포·코드에 넣지 말 것)
    kis = PyKis(
        id=os.environ.get("KIS_HTS_ID") or None,
        account=os.environ["KIS_ACCOUNT"],          # 예: "12345678-01"
        appkey=os.environ["KIS_APPKEY"],
        secretkey=os.environ["KIS_APPSECRET"],
        keep_token=True,
    )

    from stockbrief.integrations.kis import build_briefing
    from stockbrief.providers.quotes_composite import CompositeQuoteProvider
    from stockbrief.providers.quotes_pykrx import PykrxQuoteProvider
    from stockbrief.providers.quotes_yf import YfinanceQuoteProvider
    from stockbrief.providers.flow_kis import KisFlowProvider

    res = build_briefing(
        kis,
        quotes=CompositeQuoteProvider({"KR": PykrxQuoteProvider(), "US": YfinanceQuoteProvider()}),
        flow=KisFlowProvider(kis),     # 코스피 수급(선택)
        region_map={},                 # 예: {"360750": "US", "241180": "JP"}
        out_dir="out",
    )
    print("저장:", res["path"])
    print(res["markdown"][:600])


if __name__ == "__main__":
    main()
