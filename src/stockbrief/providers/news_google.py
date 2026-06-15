"""GoogleNewsProvider — Google News RSS, 키 불필요. 발행일(pubDate) N일 필터 내장."""

from __future__ import annotations

import html
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from ..models import NewsItem
from .base import NewsProvider

logger = logging.getLogger(__name__)
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return html.unescape(_TAG.sub("", text or "")).strip()


def _within(pub_dt: str, cutoff: datetime):
    try:
        d = parsedate_to_datetime(pub_dt)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        d = d.astimezone(timezone.utc)
        return d >= cutoff, d.date().isoformat()
    except Exception as e:  # noqa: BLE001
        logger.debug("발행일 파싱 실패 (%r): %s", pub_dt, e)
        return False, None


class GoogleNewsProvider(NewsProvider):
    def __init__(self, lang: str = "ko", country: str = "KR", limit: int = 6, timeout: int = 10):
        self.lang, self.country, self.limit, self.timeout = lang, country, limit, timeout

    def search(self, query: str, days: int = 7, asof=None) -> list[NewsItem]:
        now = asof or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        cutoff = now - timedelta(days=days)
        q = urllib.parse.quote(f"{query} when:{days}d")
        url = (f"https://news.google.com/rss/search?q={q}"
               f"&hl={self.lang}&gl={self.country}&ceid={self.country}:{self.lang}")
        out: list[NewsItem] = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "stockbrief"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                root = ET.fromstring(r.read())
        except Exception as e:  # noqa: BLE001
            logger.warning("Google 뉴스 조회 실패 (query=%r): %s", query, e)
            return out
        for item in root.iter("item"):
            ok, date = _within(item.findtext("pubDate"), cutoff)
            if not ok:
                continue
            link = (item.findtext("link") or "").strip()
            if not link:
                continue
            src = item.find("source")
            out.append(NewsItem(date=date, title=_clean(item.findtext("title")),
                                url=link, source=_clean(src.text) if src is not None else "Google News"))
            if len(out) >= self.limit:
                break
        return out
