# stockbrief

![python](https://img.shields.io/badge/python-3.10+-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![status](https://img.shields.io/badge/status-alpha-orange)

**보유 주식 + 시장 데이터로 데일리 브리핑을 만드는, 끼워넣기 가능한(pluggable) 엔진.**

보유 종목과 시장 데이터(시세·심리·뉴스·환율·수급)를 받아 → **시장별 국면 · 종목 별점 · 뉴스 · 점수판**을 묶은 브리핑을 산출한다. **API 키 없이도 동작**하고(무료 소스 기본 탑재), 필요하면 한국투자증권(KIS)·네이버를 끼워 정밀도를 높인다.

> ⚠️ 정보 제공용 계산 엔진이다. 투자 자문이 아니며 매매·주문 기능은 없다.
> 🚧 alpha — 결정적 계산 코어·provider·파이프라인은 동작·테스트 완료. API는 변할 수 있다.

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
    fx=FreeFxProvider(), sentiment=CnnFngProvider(), news=GoogleNewsProvider(),   # 전부 키 불필요
)
print(build_markdown(advisor.run(), AdvisorConfig.default()))
```
→ 시장별 국면 + 보유 표 + 종목 뉴스(링크) 마크다운. **API 키 0개.** (실행: `python examples/keyless_demo.py`)

---

## 특징

- **provider 패턴** — 보유·시세·감성·뉴스·환율·수급을 인터페이스 뒤로. 키 없는 기본 구현 + 선택적 고정밀(KIS·네이버)을 갈아끼운다. 빠진 provider 는 graceful degrade.
- **보유 주입** — 고정 파일이 아니라 소비 프로젝트가 보유를 넣는다(JSON·dict·증권사 잔고 API).
- **결정적/판단 분리** — 산식(평단역산·비중·국면·별점·회고%)은 순수 함수(stdlib). 매수/매도/유지 판단·서술은 동봉된 포터블 스킬(에이전트)이.
- **다(多)시장** — `region`(기반시장 US/KR/JP/CN/…)을 시장마다 **독립** 판정. 시장 추가는 설정 한 줄.

| provider | 키 불필요 기본 | 선택(고정밀) |
|---|---|---|
| 보유 Holdings | `JsonHoldingsProvider` · `DictHoldingsProvider` | 한국투자증권 잔고(`integrations.kis`) |
| 시세 Quote | `PykrxQuoteProvider`(KR) · `YfinanceQuoteProvider`(US) | `KisQuoteProvider` |
| 환율 Fx | `FreeFxProvider`(ECB) | — |
| 심리 Sentiment | `CnnFngProvider`(US) | — |
| 뉴스 News | `GoogleNewsProvider` | `NaverNewsProvider` |
| 수급 Flow | — | `KisFlowProvider` |

## 설치

```bash
pip install stockbrief                 # 코어만(stdlib) — 결정적 계산
pip install "stockbrief[quotes-kr]"    # + 무료 한국 시세(pykrx)
pip install "stockbrief[quotes-us]"    # + 무료 미국 시세(yfinance)
pip install "stockbrief[kis]"          # + 한국투자증권 고정밀(pykis)
pip install "stockbrief[all]"          # 전부
```
> 아직 PyPI 미등록 — 현재는 `pip install -e .` (소스). 

## 핵심 개념 — 시장 2종 구분

| 개념 | 필드 | 쓰임 |
|---|---|---|
| **상장지(listing)** | `market` = KR/US | 시세 엔드포인트·환율 환산 |
| **기반시장(region)** | `region` = US/KR/JP/CN/global | 시장 국면·감성 판정 |

예: 니케이225 ETF 는 `market=KR`(KRX 상장)·`region=JP`(일본 베팅). **둘을 섞지 않는다.**

## 한국투자증권(KIS) 계좌 연동

[pykis](https://github.com/Soju06/python-kis) 세션을 주면 보유를 KIS 잔고에서 자동 조회해 브리핑을 만든다:
```python
from stockbrief.integrations.kis import build_briefing
res = build_briefing(kis, out_dir="out")   # out/briefing_YYYYMMDD.md
```
생성된 마크다운을 웹 대시보드·메신저 등에 그대로 노출하면 된다. 예시: [examples/kis_account.py](examples/kis_account.py).

## 문서

| 문서 | 내용 |
|---|---|
| **[docs/USAGE.md](docs/USAGE.md)** | 설치·provider·Advisor·브리핑·설정·KIS 연동·스킬·레시피 (상세 사용법) |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 레이어·provider 패턴·데이터 계약·확장 지점·수정 가이드 |
| [examples/](examples/) | `keyless_demo.py`(키0) · `kis_account.py`(KIS 계좌) |
| [skills/](skills/) | 포터블 Claude 스킬(판단·회고) |

## 라이선스

MIT.

> 이 저장소엔 **개인 보유·계좌·키가 일절 없다.** 예시·테스트는 전부 합성 데이터.
