from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone

from .models import ThemeScore


def _parse_date(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def score_theme(rows: Iterable[dict], now: datetime | None = None) -> ThemeScore:
    items = list(rows)
    if not items:
        return ThemeScore(0, 0, 0, 0)

    now = now or datetime.now(timezone.utc)
    dates = [date for row in items if (date := _parse_date(row.get("published_at", "")))]
    recent = sum(1 for date in dates if 0 <= (now - date).days <= 30)
    prior = sum(1 for date in dates if 30 < (now - date).days <= 60)
    months = {(date.year, date.month) for date in dates}
    source_types = Counter(row.get("source_type", "unknown") for row in items)

    recurrence = min(25.0, len(items) * 2.5)
    acceleration = min(25.0, max(0.0, (recent - prior) * 4.0 + (8.0 if recent else 0.0)))
    persistence = min(25.0, len(months) * 5.0)
    breadth = min(25.0, len(source_types) * 5.0)
    return ThemeScore(recurrence, acceleration, persistence, breadth)
