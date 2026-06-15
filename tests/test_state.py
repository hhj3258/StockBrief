"""state·llm·config 확장 테스트 — 합성 데이터(개인정보 없음)."""

import pytest

from stockbrief.config import AdvisorConfig
from stockbrief.llm import build_prompt, summarize
from stockbrief.state import StateStore


def test_state_store(tmp_path):
    st = StateStore(str(tmp_path / "state.json"))
    st.record("2026-06-08", 1000)
    st.record("2026-06-15", 1100)
    st.record("2026-06-15", 1150)                  # 같은 날 → 덮어쓰기
    hist = st.history()
    assert len(hist) == 2 and hist[-1]["total_eval"] == 1150.0
    assert st.change_pct("2026-06-08") == 15.0     # 1000 → 1150 = +15%
    assert st.latest_before("2026-06-10")["date"] == "2026-06-08"  # 휴장일 폴백
    assert StateStore(str(tmp_path / "empty.json")).change_pct("2026-06-08") is None  # 데이터 없으면 None


def test_llm_helpers():
    md = "# 브리핑\n- 데이터 한 줄"
    prompt = build_prompt(md, instruction="요약하라:")
    assert "요약하라:" in prompt and md in prompt
    assert summarize(md, lambda p: "OUT:" + str(len(p))).startswith("OUT:")
    with pytest.raises(TypeError):                 # 콜러블 아니면 에러
        summarize(md, "not-callable")


def test_config_threshold_override():
    cfg = AdvisorConfig.from_dict({"thresholds": {"rsi_overheat": 80, "stop_loss_pct": -8}})
    assert cfg.thresholds["rsi_overheat"] == 80
    assert cfg.thresholds["stop_loss_pct"] == -8
    assert cfg.thresholds["max_position_pct"] == 30        # 미지정은 기본 유지
    cfg2 = AdvisorConfig.from_dict({"rsi_overheat": 75})   # 레거시 최상위 키도 지원
    assert cfg2.thresholds["rsi_overheat"] == 75
