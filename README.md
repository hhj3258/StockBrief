# stockbrief

![python](https://img.shields.io/badge/python-3.10+-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![status](https://img.shields.io/badge/status-alpha-orange)

**보유 종목과 시장 데이터를 모아 매일 포트폴리오 브리핑을 만들어 주는 Python 라이브러리입니다.**

시세·투자 심리·뉴스·환율·수급을 받아 **시장별 국면, 종목 점수, 관련 뉴스, 벤치마크 성과**를 한 장의 브리핑으로 묶어 줍니다. **API 키가 없어도** 무료 데이터 소스만으로 전부 동작하고, 한국투자증권(KIS)·네이버 키를 끼우면 정밀도가 올라갑니다.

> ⚠️ 정보 제공용 계산 도구입니다. 투자 자문이 아니고, 매매·주문 기능도 없습니다.
> 아직 alpha 단계입니다 — 계산 코어와 데이터 연동은 테스트를 거쳤지만 공개 API는 바뀔 수 있습니다.

## 빠른 시작

```python
from stockbrief.config import AdvisorConfig
from stockbrief.pipeline import Advisor
from stockbrief.briefing import build_markdown
from stockbrief.providers import DictHoldingsProvider, FreeFxProvider, CnnFngProvider, GoogleNewsProvider
from stockbrief.providers.quotes_composite import CompositeQuoteProvider
from stockbrief.providers.quotes_pykrx import PykrxQuoteProvider
from stockbrief.providers.quotes_yf import YfinanceQuoteProvider

advisor = Advisor(
    AdvisorConfig.default(),
    holdings=DictHoldingsProvider([
        {"code": "069500", "name": "KODEX200", "market": "KR", "region": "KR", "qty": 1, "avg_price": 120000, "eval_amount": 129270},
        {"ticker": "NVDA", "name": "엔비디아", "market": "US", "region": "US", "qty": 1, "avg_price_krw": 200000, "eval_amount": 311000},
    ]),
    quotes=CompositeQuoteProvider({"KR": PykrxQuoteProvider(), "US": YfinanceQuoteProvider()}),
    fx=FreeFxProvider(), sentiment=CnnFngProvider(), news=GoogleNewsProvider(),   # 모두 키 불필요
)
print(build_markdown(advisor.run(), AdvisorConfig.default()))
```

시장별 국면, 보유 종목 표, 종목별 뉴스 링크가 담긴 마크다운이 출력됩니다. **여기까지 API 키가 하나도 필요 없습니다.** (바로 실행해 보려면 `python examples/keyless_demo.py`)

## 주요 특징

- **갈아끼우는 데이터 소스(provider 구조)** — 시세·심리·뉴스·환율·수급을 공통 인터페이스 뒤에 둡니다. 무료 기본 구현이 들어 있고, 필요하면 정밀한 소스(KIS·네이버)로 교체합니다. 넣지 않은 소스는 자동으로 건너뜁니다.
- **보유 종목 주입** — 보유 목록을 코드에 고정하지 않고 쓰는 쪽에서 넣습니다(JSON 파일·딕셔너리·증권사 잔고 API).
- **계산과 판단 분리** — 비중·국면·점수 같은 숫자는 **순수 계산**(표준 라이브러리만 사용)으로 뽑고, 사고팔지 같은 **판단과 서술**은 함께 제공하는 Claude 스킬이 맡습니다.
- **여러 시장 지원** — 미국·한국·일본·중국 등 시장마다 국면을 따로 판정합니다. 시장 추가는 설정 한 줄이면 됩니다.

| 데이터 | 무료 기본(키 불필요) | 정밀 옵션 |
|---|---|---|
| 보유 종목 | `JsonHoldingsProvider` · `DictHoldingsProvider` | 한국투자증권 잔고(`integrations.kis`) |
| 시세 | `PykrxQuoteProvider`(한국) · `YfinanceQuoteProvider`(미국) | `KisQuoteProvider` |
| 환율 | `FreeFxProvider`(ECB) | — |
| 투자 심리 | `CnnFngProvider`(미국) | — |
| 뉴스 | `GoogleNewsProvider` | `NaverNewsProvider` |
| 수급 | — | `KisFlowProvider` |

## 설치

```bash
pip install stockbrief                 # 코어만 — 순수 계산(표준 라이브러리)
pip install "stockbrief[quotes-kr]"    # + 무료 한국 시세(pykrx)
pip install "stockbrief[quotes-us]"    # + 무료 미국 시세(yfinance)
pip install "stockbrief[kis]"          # + 한국투자증권 시세·잔고(pykis)
pip install "stockbrief[all]"          # 전부
```

> 아직 PyPI에 올리지 않았습니다. 지금은 소스에서 설치하세요: `pip install -e .`

## 핵심 개념

### 상장 시장(market) vs 기반 시장(region)

종목 하나에 시장 개념이 두 가지 붙습니다. 이 둘을 구분하는 것이 stockbrief의 출발점입니다.

| 개념 | 필드 | 뜻 | 쓰임 |
|---|---|---|---|
| **상장 시장** | `market` = KR / US | 종목이 실제 상장·거래되는 거래소 | 시세 조회 · 환율 환산 |
| **기반 시장** | `region` = US / KR / JP / CN / global | 종목 성과가 따라가는 경제권 | 시장 국면 · 투자 심리 판정 |

예를 들어 일본 니케이225를 추종하는 한국 상장 ETF는 `market=KR`(한국 거래소 상장)이면서 `region=JP`(일본 시장에 베팅)입니다. **두 값을 섞지 않습니다.**

### 용어

브리핑에 쓰이는 용어를 미리 정리합니다.

- **시장 국면(regime)** — 한 시장이 지금 공포~탐욕 중 어느 단계인지로 나눈 분위기.
- **종목 점수(별점)** — 종목을 0~5점으로 종합 평가한 값.
- **과열도** — 보유 종목 중 RSI가 70을 넘는 종목의 비율.
- **수급(flow)** — 외국인·기관·개인의 순매매 동향(코스피 기준).
- **투자 심리 지수** — 시장의 공포·탐욕 정도. 미국은 CNN Fear & Greed 지수를, 그 외 시장은 지표로 자체 추정합니다.
- **벤치마크 성과** — 아무것도 사고팔지 않고 그대로 들고 있었을 때 대비, 실제 매매가 만든 초과 수익.
- **회고** — 과거 한 시점과 비교해 그동안의 매매가 수익에 도움이 됐는지 사후에 평가하는 것.

## 한국투자증권(KIS) 계좌 연동

[pykis](https://github.com/Soju06/python-kis) 세션을 넘기면 보유 종목을 KIS 잔고에서 자동으로 읽어 브리핑을 만듭니다.

```python
from stockbrief.integrations.kis import build_briefing
res = build_briefing(kis, out_dir="out")   # out/briefing_YYYYMMDD.md 생성
```

만들어진 마크다운을 웹 대시보드·메신저 등에 그대로 띄우면 됩니다. 전체 예시: [examples/kis_account.py](examples/kis_account.py).

## 문서

| 문서 | 내용 |
|---|---|
| **[docs/USAGE.md](docs/USAGE.md)** | 설치부터 provider·설정·KIS 연동·스킬까지 단계별 사용법 |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 내부 구조·데이터 계약·확장 지점 (수정·기여 전에 읽기) |
| [examples/](examples/) | `keyless_demo.py`(키 0개) · `kis_account.py`(KIS 계좌 연동) |
| [skills/](skills/) | 판단·회고용 Claude 스킬 |

## 라이선스

MIT.

> 이 저장소에는 **개인 보유·계좌·키가 전혀 들어 있지 않습니다.** 예시와 테스트는 모두 합성 데이터입니다.
