"""StateStore — 일별 스냅샷 히스토리(JSON). 벤치마크·알파 계산용 가벼운 상태 저장소.

실행 시점 스냅샷만 다루던 한계를 보완한다. 매일 브리핑 시점의 평가액(+선택 메타)을 한 파일에
누적 기록해두면 어제·지난주 대비 변화율을 계산할 수 있다. SQLite 없이 JSON 한 파일이라
이식·검사·버전관리가 쉽다. (개인 데이터가 들어가므로 .gitignore 권장 — 예: state*.json)

    from stockbrief.state import StateStore
    st = StateStore("state.json")
    st.record("2026-06-15", total_eval=12_500_000)        # 매일 1회 기록(같은 날은 덮어씀)
    st.change_pct("2026-06-08")                            # 지난주 대비 변화율(%)
"""

from __future__ import annotations

import os

from .lib import dump_json, load_json


class StateStore:
    def __init__(self, path):
        self.path = path

    def _load(self) -> dict:
        return load_json(self.path) if os.path.exists(self.path) else {"snapshots": []}

    def record(self, date: str, total_eval: float, **extra) -> dict:
        """date(YYYY-MM-DD) 스냅샷 기록 — 같은 날짜는 덮어쓴다. 반환: 저장된 스냅샷."""
        data = self._load()
        snaps = [s for s in data.get("snapshots", []) if s.get("date") != date]
        snap = {"date": date, "total_eval": round(float(total_eval), 2), **extra}
        snaps.append(snap)
        snaps.sort(key=lambda s: s.get("date", ""))
        data["snapshots"] = snaps
        dump_json(data, self.path)
        return snap

    def history(self) -> list:
        return self._load().get("snapshots", [])

    def get(self, date: str):
        return next((s for s in self.history() if s.get("date") == date), None)

    def latest_before(self, date: str):
        """그 날짜 '이전' 마지막 스냅샷(휴장일이면 직전 거래일 스냅샷에 자동 매칭)."""
        prev = [s for s in self.history() if s.get("date", "") < date]
        return prev[-1] if prev else None

    def change_pct(self, date_from: str, date_to: str | None = None):
        """두 스냅샷 사이 평가액 변화율(%). 시작일이 없으면 직전 스냅샷, 종료일 미지정 시 마지막."""
        a = self.get(date_from) or self.latest_before(date_from)
        hist = self.history()
        b = self.get(date_to) if date_to else (hist[-1] if hist else None)
        if not a or not b or not a.get("total_eval"):
            return None
        return round(100.0 * (b["total_eval"] - a["total_eval"]) / a["total_eval"], 2)
