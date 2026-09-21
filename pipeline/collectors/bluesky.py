from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from pipeline.models import SourceItem
from pipeline.normalize import compact_text


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
REPOST_TYPE = "app.bsky.feed.defs#reasonRepost"


@dataclass(slots=True)
class Account:
    source_id: str
    publisher_id: str
    display_name: str
    handle: str
    did: str
    focus: str
    identity_confidence: str


@dataclass(slots=True)
class CollectionResult:
    items: list[SourceItem]
    accounts_collected: int
    errors: list[str]


def load_config(payload: dict[str, Any]) -> tuple[list[Account], list[str], set[str], int, str]:
    accounts = [Account(**row) for row in payload.get("accounts", [])]
    terms = [compact_text(value).casefold() for value in payload.get("include_terms", []) if compact_text(value)]
    domains = {value.casefold() for value in payload.get("artifact_domains", [])}
    limit = max(1, min(100, int(payload.get("per_account_limit", 50))))
    api_root = str(payload.get("api_root", "https://public.api.bsky.app")).rstrip("/")
    return accounts, terms, domains, limit, api_root


def _json(
    url: str,
    *,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ai-signal-radar/0.1"})
    for attempt in range(3):
        try:
            with opener(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS or attempt == 2:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            time.sleep(float(retry_after) if retry_after else 2**attempt)
        except URLError:
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Bluesky request failed")


def _quoted_text(embed: dict[str, Any]) -> str:
    record = embed.get("record", {}) if isinstance(embed, dict) else {}
    if isinstance(record, dict) and isinstance(record.get("record"), dict):
        record = record["record"]
    value = record.get("value", {}) if isinstance(record, dict) else {}
    return compact_text(str(value.get("text", ""))) if isinstance(value, dict) else ""


def _external_url(post: dict[str, Any], record: dict[str, Any]) -> str:
    for embed in (post.get("embed", {}), record.get("embed", {})):
        if not isinstance(embed, dict):
            continue
        candidates = [embed, embed.get("media", {})]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            external = candidate.get("external", {})
            if isinstance(external, dict) and external.get("uri"):
                return str(external["uri"])
    return ""


def _relevant(text: str, external_url: str, terms: list[str], artifact_domains: set[str]) -> bool:
    lowered = text.casefold()
    for term in terms:
        if len(term) <= 3 and term.isalnum():
            if re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", lowered):
                return True
        elif term in lowered:
            return True
    hostname = (urlparse(external_url).hostname or "").casefold()
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in artifact_domains)


def _item_id(did: str, record_key: str) -> str:
    actor = hashlib.sha256(did.encode("utf-8")).hexdigest()[:12]
    return f"bluesky:{actor}:{record_key}"


def parse_feed(
    payload: dict[str, Any],
    account: Account,
    terms: list[str],
    artifact_domains: set[str],
) -> list[SourceItem]:
    items: list[SourceItem] = []
    for entry in payload.get("feed", []):
        if (entry.get("reason") or {}).get("$type") == REPOST_TYPE:
            continue
        post = entry.get("post", {})
        author = post.get("author", {})
        record = post.get("record", {})
        if author.get("did") != account.did or record.get("reply"):
            continue
        uri = str(post.get("uri", ""))
        record_key = uri.rsplit("/", 1)[-1]
        if not record_key or record_key == uri:
            continue
        text = compact_text(str(record.get("text", "")))
        quote_text = _quoted_text(post.get("embed", {}))
        external_url = _external_url(post, record)
        searchable = compact_text(f"{text} {quote_text}")
        if not searchable or EMAIL_PATTERN.search(searchable) or not _relevant(searchable, external_url, terms, artifact_domains):
            continue
        title = text or quote_text
        if len(title) > 200:
            title = title[:197].rstrip() + "..."
        summary = quote_text if text and quote_text else ""
        if len(summary) > 160:
            summary = summary[:157].rstrip() + "..."
        post_url = f"https://bsky.app/profile/{account.handle}/post/{record_key}"
        items.append(
            SourceItem(
                id=_item_id(account.did, record_key),
                source_id=account.source_id,
                source_type="expert-social",
                title=title,
                url=post_url,
                published_at=str(record.get("createdAt") or post.get("indexedAt") or ""),
                summary=summary,
                authors=[account.display_name],
                tags=["bluesky", "expert-observation"],
                sponsor_status="not-applicable",
                metadata={
                    "actor_did": account.did,
                    "handle": account.handle,
                    "publisher_id": account.publisher_id,
                    "identity_confidence": account.identity_confidence,
                    "focus": account.focus,
                },
            )
        )
    return items


def collect(
    config: dict[str, Any],
    *,
    opener: Callable[..., Any] = urlopen,
) -> CollectionResult:
    accounts, terms, artifact_domains, limit, api_root = load_config(config)
    items: list[SourceItem] = []
    errors: list[str] = []
    collected = 0
    for account in accounts:
        query = urlencode({"actor": account.did, "filter": "posts_no_replies", "limit": limit})
        try:
            payload = _json(
                f"{api_root}/xrpc/app.bsky.feed.getAuthorFeed?{query}",
                opener=opener,
            )
            items.extend(parse_feed(payload, account, terms, artifact_domains))
            collected += 1
        except Exception as exc:
            errors.append(f"{account.handle}: {type(exc).__name__}: {exc}")
    if accounts and not collected:
        raise RuntimeError("All Bluesky account collections failed: " + "; ".join(errors))
    return CollectionResult(items=items, accounts_collected=collected, errors=errors)
