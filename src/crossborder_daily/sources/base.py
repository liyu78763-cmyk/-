from __future__ import annotations

from datetime import datetime
from typing import Protocol

from crossborder_daily.models import NewsItem


class NewsProvider(Protocol):
    name: str

    def fetch(self, since: datetime, until: datetime) -> list[NewsItem]:
        """Return news items published between since and until."""
