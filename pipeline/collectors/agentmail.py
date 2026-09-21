from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

from pipeline.models import SourceItem
from pipeline.normalize import compact_text


API_ROOT = "https://api.agentmail.to/v0"
ALPHASIGNAL_ARCHIVE = "https://alphasignal.ai/archive"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
IGNORED_LINK_TEXT = re.compile(
    r"^(?:sign\s*up|work with us|follow on|archive|read more|forward|partner with us|"
    r"register|awesome|decent|not great|unsubscribe|get \$|start a trial)",
    re.I,
)
SPONSOR_CONTEXT = re.compile(r"\b(?:presented by|in partnership with|partner with us)\b", re.I)
LEADING_MARKER = re.compile(r"^(?:[▸▶→•]\s*)?(?:\d+[.)]\s*)?")


@dataclass(slots=True)
class NewsletterDefinition:
    source_id: str
    source_type: str
    sender_domains: tuple[str, ...]
    parser: str


@dataclass(slots=True)
class CollectionResult:
    items: list[SourceItem]
    next_after: str | None
    messages_seen: int
    messages_matched: int


@dataclass(slots=True)
class _Token:
    text: str
    href: str = ""


class _LinkDocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[_Token] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href") or ""
            self._link_text = []

    def handle_data(self, data: str) -> None:
        value = compact_text(data)
        if not value:
            return
        if self._href is not None:
            self._link_text.append(value)
        else:
            self.tokens.append(_Token(value))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            text = compact_text(" ".join(self._link_text))
            if text:
                self.tokens.append(_Token(text, self._href))
            self._href = None
            self._link_text = []


class AgentMailClient:
    def __init__(
        self,
        api_key: str,
        *,
        api_root: str = API_ROOT,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        if not api_key:
            raise ValueError("AgentMail API key is required")
        self.api_key = api_key
        self.api_root = api_root.rstrip("/")
        self.opener = opener

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = urlencode([(key, value) for key, value in (params or {}).items() if value is not None])
        url = f"{self.api_root}{path}" + (f"?{query}" if query else "")
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "User-Agent": "ai-signal-radar/0.1",
            },
        )
        for attempt in range(3):
            try:
                with self.opener(request, timeout=30) as response:
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
        raise RuntimeError("AgentMail request failed")

    def list_messages(self, inbox_id: str, after: str | None = None) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            payload = self._get(
                f"/inboxes/{quote(inbox_id, safe='')}/messages",
                {
                    "limit": 100,
                    "after": after,
                    "ascending": "true",
                    "page_token": page_token,
                },
            )
            messages.extend(payload.get("messages", []))
            page_token = payload.get("next_page_token")
            if not page_token:
                return messages

    def get_message(self, inbox_id: str, message_id: str) -> dict[str, Any]:
        return self._get(
            f"/inboxes/{quote(inbox_id, safe='')}/messages/{quote(message_id, safe='')}"
        )


def load_definitions(path: Path) -> list[NewsletterDefinition]:
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    definitions = []
    for row in payload.get("newsletters", []):
        if not row.get("enabled", True):
            continue
        definitions.append(
            NewsletterDefinition(
                source_id=row["source_id"],
                source_type=row.get("source_type", "newsletter"),
                sender_domains=tuple(value.lower() for value in row.get("sender_domains", [])),
                parser=row.get("parser", "issue"),
            )
        )
    return definitions


def _sender_domain(value: str) -> str:
    address = parseaddr(value)[1].lower()
    return address.rsplit("@", 1)[-1] if "@" in address else ""


def _definition_for(message: dict[str, Any], definitions: list[NewsletterDefinition]) -> NewsletterDefinition | None:
    domain = _sender_domain(str(message.get("from", "")))
    for definition in definitions:
        if any(domain == allowed or domain.endswith(f".{allowed}") for allowed in definition.sender_domains):
            return definition
    return None


def _public_issue_url(html: str) -> str:
    for match in re.finditer(r"https?://[^\s\"'<>]+", html or ""):
        parsed = urlparse(match.group(0).replace("&amp;", "&"))
        campaign_id = parse_qs(parsed.query).get("cid", [""])[0]
        if campaign_id and re.fullmatch(r"[a-zA-Z0-9_-]{8,64}", campaign_id):
            return f"https://alphasignal.ai/email/{campaign_id}"
    return ALPHASIGNAL_ARCHIVE


def _candidate_title(value: str) -> str | None:
    title = compact_text(LEADING_MARKER.sub("", value)).strip(" -|•")
    if len(title) < 32 or len(title.split()) < 5 or IGNORED_LINK_TEXT.search(title):
        return None
    return title


def _stable_item_id(source_id: str, published_at: str, title: str) -> str:
    material = f"{source_id}|{published_at[:10]}|{compact_text(title).casefold()}"
    return f"{source_id}:{hashlib.sha256(material.encode('utf-8')).hexdigest()[:20]}"


def _overlap_after(value: str | None) -> str | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed - timedelta(minutes=5)).isoformat()


def parse_alphasignal(message: dict[str, Any], definition: NewsletterDefinition) -> list[SourceItem]:
    html = str(message.get("extracted_html") or message.get("html") or "")
    parser = _LinkDocumentParser()
    parser.feed(html)
    public_url = _public_issue_url(html)
    published_at = str(message.get("timestamp") or message.get("created_at") or "")

    sponsor_hrefs: set[str] = set()
    for index, token in enumerate(parser.tokens):
        if not token.href:
            continue
        context = " ".join(part.text for part in parser.tokens[max(0, index - 2) : index + 2])
        if SPONSOR_CONTEXT.search(context):
            sponsor_hrefs.add(token.href)

    candidates: dict[str, dict[str, Any]] = {}
    for token in parser.tokens:
        if not token.href:
            continue
        parsed = urlparse(token.href.replace("&amp;", "&"))
        if not parsed.hostname or not parsed.hostname.endswith("alphasignal.ai"):
            continue
        title = _candidate_title(token.text)
        if not title:
            continue
        key = compact_text(title).casefold()
        row = candidates.setdefault(key, {"title": title, "sponsored": False})
        row["sponsored"] = row["sponsored"] or token.href in sponsor_hrefs

    items = []
    for row in candidates.values():
        items.append(
            SourceItem(
                id=_stable_item_id(definition.source_id, published_at, row["title"]),
                source_id=definition.source_id,
                source_type=definition.source_type,
                title=row["title"],
                url=public_url,
                published_at=published_at,
                summary="Newsletter-curated item; the underlying claim has not been independently verified.",
                sponsor_status="sponsored" if row["sponsored"] else "editorial",
            )
        )
    return items


def parse_issue(message: dict[str, Any], definition: NewsletterDefinition) -> list[SourceItem]:
    title = compact_text(str(message.get("subject") or "Untitled newsletter issue"))
    published_at = str(message.get("timestamp") or message.get("created_at") or "")
    homepage = ALPHASIGNAL_ARCHIVE if definition.source_id == "alphasignal" else ""
    return [
        SourceItem(
            id=_stable_item_id(definition.source_id, published_at, title),
            source_id=definition.source_id,
            source_type=definition.source_type,
            title=title,
            url=homepage,
            published_at=published_at,
            summary="Newsletter issue metadata; no raw mailbox content is published.",
            sponsor_status="unknown",
        )
    ]


def collect(
    api_key: str,
    inbox_id: str,
    definitions: list[NewsletterDefinition],
    *,
    after: str | None = None,
    client: AgentMailClient | None = None,
) -> CollectionResult:
    client = client or AgentMailClient(api_key)
    messages = client.list_messages(inbox_id, after=_overlap_after(after))
    items: list[SourceItem] = []
    matched = 0
    timestamps = [str(row.get("timestamp") or row.get("created_at") or "") for row in messages]

    for metadata in messages:
        definition = _definition_for(metadata, definitions)
        if not definition:
            continue
        matched += 1
        message_id = str(metadata.get("message_id") or "")
        if not message_id:
            raise ValueError("AgentMail message is missing message_id")
        message = client.get_message(inbox_id, message_id)
        if definition.parser == "alphasignal":
            parsed = parse_alphasignal(message, definition)
            items.extend(parsed or parse_issue(message, definition))
        else:
            items.extend(parse_issue(message, definition))

    next_after = max((value for value in timestamps if value), default=after)
    return CollectionResult(items=items, next_after=next_after, messages_seen=len(messages), messages_matched=matched)


def read_after(path: Path) -> str | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("after")


def write_after(path: Path, value: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "after": value,
        "updated_at": datetime.now(timezone.utc).isoformat() if value else None,
        "note": "Public-safe ingestion cursor; no mailbox or message identifiers are stored.",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
