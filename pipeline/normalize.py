from __future__ import annotations

import re
import unicodedata


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def canonical_url(url: str) -> str:
    return (url or "").split("#", 1)[0].rstrip("/")
