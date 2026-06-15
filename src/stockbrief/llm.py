"""LLM 연동 편의 — 데이터/마크다운 → "브리핑 글" 한 줄 연결.

**원칙: 패키지는 API 키도, 특정 벤더(anthropic/openai)도 다루지 않는다.** 키 관리·모델
선택은 소비자 몫이라, 여기선 사용자가 넘긴 콜러블 `llm_fn(prompt) -> str` 만 호출한다.
(StockBrief 의 "계산은 패키지, 판단·서술은 LLM/스킬" 분리를 지키면서 보일러플레이트만 제거.)

    from stockbrief.briefing import build_markdown
    from stockbrief.llm import summarize
    md = build_markdown(advisor.run(), config)
    def my_llm(prompt):                       # 사용자 LLM 호출(키는 사용자 환경에서)
        return anthropic_client.messages.create(...).content[0].text
    text = summarize(md, my_llm)              # 데이터 → 마크다운 → LLM 산문
"""

from __future__ import annotations

DEFAULT_INSTRUCTION = (
    "아래는 보유 포트폴리오의 오늘자 데이터(시장 국면·비중·시세·뉴스)입니다. "
    "데이터 근거를 인용하며, 종목을 가로지르는 구조(현금·쏠림·수급·국면)와 주의할 점을 "
    "5~10줄의 자연스러운 한국어 브리핑으로 정리하세요. 매수/매도 단정·투자 권유는 피하고 "
    "정보 제공 관점으로 서술합니다. 뉴스는 제목과 함께 근거로만 언급하세요."
)


def build_prompt(markdown: str, *, instruction: str | None = None) -> str:
    """LLM 에 바로 넣을 프롬프트. (instruction) + 구분선 + (브리핑 마크다운)."""
    return f"{instruction or DEFAULT_INSTRUCTION}\n\n---\n{markdown}"


def summarize(markdown: str, llm_fn, *, instruction: str | None = None) -> str:
    """build_prompt 를 만들어 사용자 llm_fn 으로 산문 브리핑을 받는다.

    llm_fn: prompt(str) 를 받아 텍스트(str) 를 돌려주는 사용자 콜러블(키는 사용자 환경에서).
    """
    if not callable(llm_fn):
        raise TypeError("summarize() 에는 llm_fn(prompt)->str 콜러블이 필요합니다")
    return llm_fn(build_prompt(markdown, instruction=instruction))
