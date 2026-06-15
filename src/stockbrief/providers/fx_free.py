"""FreeFxProvider — USD/KRW 환율, 키 불필요. frankfurter(ECB) → open.er-api 폴백."""

from __future__ import annotations

import json
import urllib.request

from .base import FxProvider

_SOURCES = [
    ("https://api.frankfurter.app/latest?from=USD&to=KRW",
     lambda d: (d["rates"]["KRW"], d.get("date"))),
    ("https://open.er-api.com/v6/latest/USD",
     lambda d: (d["rates"]["KRW"], d.get("time_last_update_utc"))),
]


class FreeFxProvider(FxProvider):
    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.last = None  # {"USDKRW", "source", "asof"}

    def usdkrw(self) -> float | None:
        for url, parse in _SOURCES:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "stockbrief"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    d = json.loads(r.read().decode("utf-8"))
                rate_raw, asof = parse(d)
                rate = round(float(rate_raw), 2)
                self.last = {"USDKRW": rate, "source": url.split("/")[2], "asof": asof}
                return rate
            except Exception:  # noqa: BLE001
                continue
        return None
