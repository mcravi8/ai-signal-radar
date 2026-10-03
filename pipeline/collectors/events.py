from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from typing import Any

from pipeline.models import SourceItem
from pipeline.normalize import compact_text


USER_AGENT = "ai-signal-radar/0.1 (public research dashboard; https://github.com/mcravi8/ai-signal-radar)"


def _fetch(url: str, accept: str = "text/html, application/json;q=0.9, */*;q=0.8") -> bytes:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def parse_event_json(source: dict[str, Any], payload: bytes) -> list[SourceItem]:
    data = json.loads(payload)
    sessions = data.get("sessions", [])
    allowed_types = set(source.get("include_types", []))
    priority_tracks = source.get("priority_tracks", [])
    priority = {track: index for index, track in enumerate(priority_tracks)}
    max_per_track = int(source.get("max_per_track", 3))
    limit = int(source.get("limit", 50))
    eligible = [
        session
        for session in sessions
        if (not allowed_types or session.get("type") in allowed_types)
        and (not priority_tracks or session.get("track") in priority)
    ]
    eligible.sort(
        key=lambda session: (
            priority.get(session.get("track", ""), len(priority)),
            session.get("day", ""),
            session.get("time", ""),
            session.get("title", ""),
        )
    )
    selected: list[dict[str, Any]] = []
    track_counts: Counter[str] = Counter()
    for session in eligible:
        track = session.get("track", "Unassigned")
        if track_counts[track] >= max_per_track:
            continue
        selected.append(session)
        track_counts[track] += 1
        if len(selected) == limit:
            break

    items = []
    seen_sessions: set[tuple[str, str]] = set()
    schedule_url = source.get("homepage_url", source["data_url"])
    event_id = source["event_id"]
    for session in selected:
        title = compact_text(session.get("title", ""))
        if not title:
            continue
        track = compact_text(session.get("track", ""))
        day = compact_text(session.get("day", ""))
        time = compact_text(session.get("time", ""))
        session_key = (title.casefold(), day.casefold())
        if session_key in seen_sessions:
            continue
        seen_sessions.add(session_key)
        items.append(
            SourceItem(
                id=f"{source['id']}:{_digest(event_id, title, day, time)}",
                source_id=source["id"],
                source_type="event-session",
                title=title,
                url=schedule_url,
                published_at=source["published_at"],
                summary=compact_text(session.get("description", ""))[:1200],
                authors=[compact_text(name) for name in session.get("speakers", []) if compact_text(name)],
                tags=[value for value in ["event-program", track, session.get("type", "")] if value],
                sponsor_status="sponsored-session" if session.get("type") == "sponsor" else "organizer-program",
                event_ids=[event_id],
                metadata={
                    "event_id": event_id,
                    "event_record_type": "session",
                    "event_track": track,
                    "event_day": day,
                },
            )
        )
    return items


class _ProceedingsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._capture = False
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "a" and values.get("title", "").casefold() == "paper title":
            self._capture = True
            self._href = values.get("href", "")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._capture:
            title = compact_text(html.unescape(" ".join(self._text)))
            if title and self._href:
                self.links.append((self._href, title))
            self._capture = False
            self._href = ""
            self._text = []


def parse_proceedings(source: dict[str, Any], payload: bytes) -> list[SourceItem]:
    parser = _ProceedingsParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    terms = [term.casefold() for term in source.get("include_terms", [])]
    candidates = [
        (href, title)
        for href, title in parser.links
        if not terms or any(term in title.casefold() for term in terms)
    ]
    candidates.sort(key=lambda item: item[1].casefold())
    event_id = source["event_id"]
    base_url = source["proceedings_url"]
    return [
        SourceItem(
            id=f"{source['id']}:{_digest(event_id, href)}",
            source_id=source["id"],
            source_type="event-paper",
            title=title,
            url=urllib.parse.urljoin(base_url, href),
            published_at=source["published_at"],
            tags=["event-paper", "conference-proceedings"],
            artifact_urls=[urllib.parse.urljoin(base_url, href)],
            sponsor_status="not-applicable",
            event_ids=[event_id],
            metadata={
                "event_id": event_id,
                "event_record_type": "paper",
                "artifact_url": urllib.parse.urljoin(base_url, href),
            },
        )
        for href, title in candidates[: int(source.get("limit", 40))]
    ]


class _DevpostParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.projects: list[dict[str, Any]] = []
        self._project: dict[str, Any] | None = None
        self._capture = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag.casefold() == "a" and "link-to-software" in classes:
            self._project = {"url": values.get("href", ""), "title": "", "tagline": "", "winner": False}
        if not self._project:
            return
        if tag.casefold() == "h5":
            self._capture = "title"
            self._text = []
        elif tag.casefold() == "p" and "tagline" in classes:
            self._capture = "tagline"
            self._text = []
        elif tag.casefold() == "img" and values.get("alt", "").casefold() == "winner":
            self._project["winner"] = True

    def handle_data(self, data: str) -> None:
        if self._project and self._capture:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        lower = tag.casefold()
        if self._project and self._capture and ((lower == "h5" and self._capture == "title") or (lower == "p" and self._capture == "tagline")):
            self._project[self._capture] = compact_text(html.unescape(" ".join(self._text)))
            self._capture = ""
            self._text = []
        if lower == "a" and self._project:
            if self._project.get("title") and self._project.get("url"):
                self.projects.append(self._project)
            self._project = None
            self._capture = ""
            self._text = []


def parse_devpost(source: dict[str, Any], payloads: list[bytes]) -> list[SourceItem]:
    records: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        parser = _DevpostParser()
        parser.feed(payload.decode("utf-8", errors="replace"))
        for project in parser.projects:
            records[project["url"]] = project
    ordered = sorted(records.values(), key=lambda item: (not item["winner"], item["title"].casefold()))
    event_id = source["event_id"]
    items = []
    for project in ordered[: int(source.get("limit", 30))]:
        tags = ["hackathon-project"]
        if project["winner"]:
            tags.append("event-winner")
        items.append(
            SourceItem(
                id=f"{source['id']}:{_digest(event_id, project['url'])}",
                source_id=source["id"],
                source_type="hackathon-project",
                title=project["title"],
                url=project["url"],
                published_at=source["published_at"],
                summary=project["tagline"][:1200],
                tags=tags,
                projects=[project["title"]],
                artifact_urls=[project["url"]],
                sponsor_status="hackathon-submission",
                event_ids=[event_id],
                metadata={
                    "event_id": event_id,
                    "event_record_type": "project",
                    "winner": bool(project["winner"]),
                    "artifact_url": project["url"],
                },
            )
        )
    return items


def collect_source(source: dict[str, Any]) -> list[SourceItem]:
    collection = source.get("collection")
    if collection == "event-json":
        return parse_event_json(source, _fetch(source["data_url"], "application/json, */*;q=0.8"))
    if collection == "conference-proceedings":
        return parse_proceedings(source, _fetch(source["proceedings_url"]))
    if collection == "devpost-gallery":
        pages = []
        for page in range(1, int(source.get("pages", 1)) + 1):
            separator = "&" if "?" in source["gallery_url"] else "?"
            pages.append(_fetch(f"{source['gallery_url']}{separator}page={page}"))
        return parse_devpost(source, pages)
    raise ValueError(f"Unsupported event collection: {collection}")


def _issue_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    pattern = re.compile(r"^###\s+(.+?)\s*$\n+(.*?)(?=^###\s+|\Z)", re.M | re.S)
    for heading, value in pattern.findall(body or ""):
        cleaned = compact_text(value.replace("_No response_", ""))
        fields[heading.casefold()] = cleaned
    return fields


def parse_reviewed_social_issues(
    issues: list[dict[str, Any]],
    event_config: dict[str, Any],
) -> list[SourceItem]:
    from pipeline.events import load_social_links

    rows = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        fields = _issue_fields(issue.get("body", ""))
        event_id = fields.get("event id", "")
        platform = fields.get("platform", "").casefold()
        artifact_text = fields.get("linked public artifacts", "")
        artifact_urls = re.findall(r"https://[^\s,]+", artifact_text)
        rows.append(
            {
                "id": f"social-link:github-issue-{issue['number']}",
                "platform": platform,
                "post_url": fields.get("public post url", ""),
                "author_name": fields.get("author name", ""),
                "published_at": fields.get("published date", ""),
                "event_ids": [event_id] if event_id else [],
                "observation": fields.get("original observation", ""),
                "linked_urls": artifact_urls,
                "tags": ["reviewed-github-submission"],
            }
        )
    return load_social_links({"links": rows}, event_config)


def collect_reviewed_social_issues(
    repository: str,
    token: str,
    event_config: dict[str, Any],
) -> list[SourceItem]:
    label = event_config.get("social_inbox", {}).get("review_label", "event-signal-reviewed")
    query = urllib.parse.urlencode({"labels": label, "state": "all", "per_page": 100})
    url = f"https://api.github.com/repos/{repository}/issues?{query}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        issues = json.loads(response.read())
    return parse_reviewed_social_issues(issues, event_config)
