# stockbrief 사용법

보유 + 시장 데이터 → 데일리 브리핑. provider 를 끼워 쓰는 방식이라 **필요한 만큼만** 연결하면 된다.
(개요는 [README](../README.md), 내부 구조는 [ARCHITECTURE](../ARCHITECTURE.md).)

---

## 1. 설치

```bash
pip install "stockbrief[quotes-kr,quotes-us]"   # 무료 시세(pykrx·yfinance·pandas)
pip install "stockbrief[kis]"                   # 한국투자증권 고정밀(pykis)
pip install "stockbrief[all]"                   # 전부
# 개발: pip install -e ".[dev]" 후  python -m pytest
```
코어(`stockbrief.lib`·metrics·benchmark·reconcile·retrospect·config·models)는 **stdlib만** 쓴다. 시세 provider 만 pandas/pykrx/yfinance/pykis 가 필요.

---

## 2. 가장 빠른 길 — Advisor

`Advisor` 가 provider 들을 묶어 `run()` 한 번에 브리핑 입력을 만든다. **준 provider 만 쓰고 없는 건 건너뛴다.**

```python
from stockbrief.config import AdvisorConfig
from stockbrief.pipeline import Advisor
from stockbrief.briefing import build_markdown
from stockbrief.providers import DictHoldingsProvider, FreeFxProvider, CnnFngProvider, GoogleNewsProvider
from stockbrief.providers.quotes_composite import CompositeQuoteProvider
from stockbrief.providers.quotes_pykrx import PykrxQuoteProvider
from stockbrief.providers.quotes_yf import YfinanceQuoteProvider

advisor = Advisor(
    config=AdvisorConfig.default(),
    holdings=DictHoldingsProvider([...]),                         # 필수
    quotes=CompositeQuoteProvider({"KR": PykrxQuoteProvider(),    # 선택
                                   "US": YfinanceQuoteProvider()}),
    fx=FreeFxProvider(),         # 선택 — US 평가 원화환산
    sentiment=CnnFngProvider(),  # 선택 — 미국 F&G
    news=GoogleNewsProvider(),   # 선택 — 종목 뉴스
    naver_news=None,             # 선택 — 한국상장 종목은 네이버로
    flow=None,                   # 선택 — 코스피 수급(KisFlowProvider)
)
inputs = advisor.run(news_days=7)        # → BriefingInputs
md = build_markdown(inputs, advisor.config, title="오늘 브리핑", date="2026-06-15")
```

`run()` 이 돌려주는 **BriefingInputs** (구조화 데이터, 대시보드/LLM 이 바로 사용):

| 필드 | 내용 |
|---|---|
| `regions` | 시장별 국면 `{region: {flag, weight_pct, n, label, tone, detail}}` |
| `weights` | 종목 비중 `{key: {name, eval, weight_pct}}` |
| `overheat` | `(ratio, hot, have)` 과열도(RSI>70 비율) |
| `quotes` | `{key: 시세 dict}` (price·rate·rsi14·ma·ma_align·w52_*) + `_fx` |
| `news` | `{key: [NewsItem...]}` |
| `fx`·`sentiment`·`flow`·`total_eval`·`holdings`·`tradable` | 부가 |

---

## 3. 보유(Holdings) 주입 — 가장 중요

브리핑의 유일한 **필수** 입력. 정규화 형태(`Position`)로 들어가면 어떤 소스든 된다.

### 3a. dict 리스트 (인메모리)
```python
from stockbrief.providers import DictHoldingsProvider
DictHoldingsProvider([
    {"code": "069500", "name": "KODEX200", "market": "KR", "region": "KR",
     "qty": 1, "avg_price": 120000, "eval_amount": 129270, "profit_pct": 7.7},
    {"ticker": "NVDA", "name": "엔비디아", "market": "US", "region": "US",
     "qty": 1, "avg_price_krw": 200000, "eval_amount": 311000, "profit_pct": 55.0},
], cash=1_000_000)
```
- KR 은 `code`+`avg_price`, US 는 `ticker`+`avg_price_krw`(원화 환산 평단).
- `region` 생략 시 `market` 으로 폴백. `eval_amount`/`profit_pct` 는 선택(있으면 표/비중에 사용).

### 3b. JSON 파일
```python
from stockbrief.providers import JsonHoldingsProvider
JsonHoldingsProvider("holdings.json")   # {"tradable_holdings": [...], "trades_*": [...], "context_assets": {...}}
```

### 3c. 증권사 잔고 API (직접 어댑터)
`HoldingsProvider` 를 구현해 `holdings() -> Holdings` 만 돌려주면 된다. (한국투자증권은 `integrations.kis.KisHoldingsProvider` 제공 → §7)

---

## 4. provider 카탈로그

```python
# 시세
from stockbrief.providers.quotes_pykrx import PykrxQuoteProvider       # KR, 키0
from stockbrief.providers.quotes_yf import YfinanceQuoteProvider       # US, 키0
from stockbrief.providers.quotes_composite import CompositeQuoteProvider  # market별 라우팅
from stockbrief.providers.quotes_kis import KisQuoteProvider           # 선택: KisQuoteProvider(session, get_quote, get_daily_ohlcv)
# 환율·심리·뉴스·수급
from stockbrief.providers import FreeFxProvider, CnnFngProvider, GoogleNewsProvider
from stockbrief.providers.news_naver import NaverNewsProvider          # NaverNewsProvider(client_id, client_secret) 또는 NAVER_CLIENT_ID/SECRET 환경변수
from stockbrief.providers.flow_kis import KisFlowProvider              # KisFlowProvider(pykis_session)
```
- **네이버 키 없으면** Advisor 는 자동으로 구글로 폴백.
- **시세 provider 없으면** 국면은 보유만으로 제한(추세·과열 미산출). FX 없으면 US 평가 eval 폴백.

---

## 5. 설정 (AdvisorConfig)

```python
from stockbrief.config import AdvisorConfig
cfg = AdvisorConfig.default()                    # 내장 기본(US/KR/JP/CN/global)
cfg = AdvisorConfig.from_yaml("stockbrief.yaml") # YAML
cfg = AdvisorConfig.from_dict({...})             # dict
```
주요 키:
```yaml
regions:                       # 시장 레지스트리(확장 지점) — 시장 추가 = 여기 한 줄 + 보유 region 태그
  US: { sentiment: cnn_fng, trend_proxy: "360750", flag: "🇺🇸" }
  KR: { trend_proxy: "069500", flow: kis, flag: "🇰🇷" }
  JP: { trend_proxy: "241180", flag: "🇯🇵" }
instrument_themes: { "069500": 한국대형지수, ... }   # 종목→테마(집중도용)
high_vol_themes: [우주테크, 양자컴퓨팅]               # 별점 비중적정 −0.5
news_queries:                                       # 종목별 넓은 검색어
  "NVDA": { primary: 엔비디아, kr: [AI 반도체, HBM], en: [NVIDIA] }
thresholds: { stop_loss_pct: -10, max_position_pct: 30, target_cash_pct: 25 }
```
- `trend_proxy`: 그 시장 추세 판정용 지수 종목코드(시세 필요). `sentiment: cnn_fng` 인 시장만 F&G 점수, 나머지는 `computed_sentiment` 추정.

---

## 6. 결정적 코어만 쓰기 (provider 없이)

브리핑 파이프라인 없이 산식만 필요하면:
```python
from stockbrief.lib import region_regime, star_score, weights, overheat_ratio
from stockbrief.metrics import all_regions
from stockbrief.benchmark import my_value, resolve_fx, excess_pct
from stockbrief.reconcile import reconcile          # 거래 diff → trades + 순현금흐름
from stockbrief.retrospect import evaluate          # 회고 % 평가

region_regime(27.5, "혼조", -1.2, 0.0)               # → ("공포 우위", {...})
star_score(4, 3.5, 4.5, 3.5)                         # → 3.5
all_regions(tradable, quotes, cfg.regions, cnn_score=34.0, investor=flow)
```

---

## 7. 한국투자증권(KIS) 계좌 연동

[pykis](https://github.com/Soju06/python-kis) 세션을 주면 보유를 KIS 잔고에서 자동 조회해 브리핑 파일을 만든다:
```python
from stockbrief.integrations.kis import build_briefing
from stockbrief.providers.quotes_composite import CompositeQuoteProvider
from stockbrief.providers.quotes_pykrx import PykrxQuoteProvider
from stockbrief.providers.quotes_yf import YfinanceQuoteProvider
from stockbrief.providers.flow_kis import KisFlowProvider

result = build_briefing(
    kis,                                   # pykis 세션(본인 KIS 앱키/계좌)
    quotes=CompositeQuoteProvider({"KR": PykrxQuoteProvider(), "US": YfinanceQuoteProvider()}),  # 키0 시세(선택)
    region_map={"360750": "US", "241180": "JP"},   # KR 상장이지만 기반시장 다른 종목
    flow=KisFlowProvider(kis),             # 코스피 수급(선택)
    out_dir="out",
)
# result = {"markdown", "path": "out/briefing_YYYYMMDD.md", "date"}
```
- 보유만 KIS, 시세는 키 불필요(pykrx/yfinance)로 섞어 쓸 수 있다. 시세도 KIS 로 하려면 `quotes=KisQuoteProvider(...)`.
- 생성된 마크다운을 웹 대시보드·메신저 등에 그대로 노출하면 된다(예: `examples/kis_account.py`).

---

## 8. 판단·서술 스킬 (선택)

stockbrief 는 **데이터·산식**까지만 한다. 매수/매도/유지 **판단 + 별점 + 산문**을 원하면 `skills/` 의
포터블 Claude 스킬을 소비 프로젝트 `.claude/skills/` 로 복사한다. 스킬이 BriefingInputs/마크다운을 받아
4요소 별점·액션·리밸런싱·'오늘의 고찰'을 작성한다. (계산=패키지, 판단=스킬)

---

## 9. 레시피

- **키 0개 풀 브리핑**: §2 그대로 (pykrx·yfinance·CNN·Google·FX).
- **한국만**: `quotes=PykrxQuoteProvider()`, US 종목 없으면 yfinance 불필요.
- **시세 없이 가볍게**: `quotes=None` → 보유·비중·뉴스만(국면은 제한).
- **KIS 고정밀**: `quotes=KisQuoteProvider(session, get_quote, get_daily_ohlcv)` + `flow=KisFlowProvider(session)`.
- **한국 뉴스 강화**: `naver_news=NaverNewsProvider()` (NAVER_CLIENT_ID/SECRET) — 한국상장 종목은 네이버로.

## 10. 주의

- 정보 제공용. 매매·주문 없음.
- 평단/평가는 입력 통화 기준(US 는 원화환산 평단 권장). % 비교라 통화만 일치하면 됨.
- 무료 시세는 지연/장막판 차이 가능. 장중 정밀·실시간이 필요하면 KIS provider.
- `computed_sentiment`(KR/JP/CN 추정 감성)는 **공식 지수 아님** — RSI·52주·추세(+수급) 합성.
