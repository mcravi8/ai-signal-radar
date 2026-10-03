from __future__ import annotations

import math
import re
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import SourceItem
from .normalize import canonical_url, compact_text, slugify


EVENT_TYPES = {"research-conference", "developer-conference", "vendor-conference", "hackathon"}
SOCIAL_PLATFORMS = {"linkedin": "linkedin-event-links", "x": "x-event-links"}
ARTIFACT_TYPES = {"event-paper", "hackathon-project", "repository"}
TECHNICAL_CHANNELS = {"paper", "paper-curation", "repository", "event-program", "hackathon-gallery", "first-party-lab"}


def _date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_event_config(config: dict[str, Any]) -> None:
    if config.get("version") != 1:
        raise ValueError("Event policy version must be 1")
    required_policy = {"purpose", "event_attention", "technical_substance", "echo_control", "claims", "persistence", "copyright"}
    missing_policy = required_policy.difference(config.get("policy", {}))
    if missing_policy:
        raise ValueError(f"Event policy is missing: {', '.join(sorted(missing_policy))}")
    seen: set[str] = set()
    for event in config.get("events", []):
        event_id = event.get("id", "")
        if not event_id or event_id in seen:
            raise ValueError(f"Event id is missing or duplicated: {event_id!r}")
        seen.add(event_id)
        if event.get("event_type") not in EVENT_TYPES:
            raise ValueError(f"Unsupported event type for {event_id}")
        start = _date(event.get("start_date", ""))
        end = _date(event.get("end_date", ""))
        if not start or not end or end < start:
            raise ValueError(f"Invalid event dates for {event_id}")
        if not event.get("official_url", "").startswith("https://"):
            raise ValueError(f"Event {event_id} needs a public HTTPS URL")


def load_social_links(payload: dict[str, Any], config: dict[str, Any]) -> list[SourceItem]:
    valid_event_ids = {event["id"] for event in config.get("events", [])}
    prohibited = set(config.get("social_inbox", {}).get("prohibited_fields", []))
    required = set(config.get("social_inbox", {}).get("required_fields", []))
    seen: set[str] = set()
    items: list[SourceItem] = []
    for row in payload.get("links", []):
        present_prohibited = prohibited.intersection(row)
        if present_prohibited:
            raise ValueError(f"Social link {row.get('id', '<unknown>')} contains prohibited fields: {', '.join(sorted(present_prohibited))}")
        missing = {field for field in required if not row.get(field)}
        if missing:
            raise ValueError(f"Social link {row.get('id', '<unknown>')} is missing: {', '.join(sorted(missing))}")
        item_id = row["id"]
        if item_id in seen:
            raise ValueError(f"Duplicate social link id: {item_id}")
        seen.add(item_id)
        platform = row["platform"].casefold()
        if platform not in SOCIAL_PLATFORMS:
            raise ValueError(f"Unsupported social platform: {platform}")
        event_ids = list(dict.fromkeys(row["event_ids"]))
        unknown = set(event_ids).difference(valid_event_ids)
        if unknown:
            raise ValueError(f"Social link {item_id} references unknown events: {', '.join(sorted(unknown))}")
        post_url = row["post_url"]
        host = urllib.parse.urlparse(post_url).hostname or ""
        expected = "linkedin.com" if platform == "linkedin" else "x.com"
        if not (host == expected or host.endswith(f".{expected}")):
            raise ValueError(f"Social link {item_id} URL does not match {platform}")
        observation = compact_text(row["observation"])
        if len(observation) > 700:
            raise ValueError(f"Social link {item_id} observation exceeds 700 characters")
        linked_urls = [url for url in row.get("linked_urls", []) if str(url).startswith("https://")]
        items.append(
            SourceItem(
                id=item_id,
                source_id=SOCIAL_PLATFORMS[platform],
                source_type="curated-social",
                title=observation,
                url=post_url,
                published_at=row["published_at"],
                summary="Analyst-written observation linked to the original public post.",
                authors=[row["author_name"]],
                tags=[platform, "event-observation", *row.get("tags", [])],
                event_ids=event_ids,
                artifact_urls=linked_urls,
                sponsor_status="unknown",
                metadata={
                    "event_id": event_ids[0],
                    "event_record_type": "observation",
                    "platform": platform,
                    "author_url": row.get("author_url", ""),
                },
            )
        )
    return items


def assign_event_ids(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach explicit or bounded event context without broad event-word matching."""
    events = config.get("events", [])
    for row in rows:
        if not row.get("artifact_urls"):
            row.pop("artifact_urls", None)
        assigned = set(row.get("event_ids", []))
        source_id = row.get("source_id", "")
        published = _date(row.get("published_at", ""))
        searchable = " ".join(
            [row.get("title", ""), row.get("summary", ""), " ".join(row.get("tags", []))]
        ).casefold()
        row_url = canonical_url(row.get("url", ""))
        for event in events:
            event_id = event["id"]
            if source_id in event.get("source_ids", []):
                assigned.add(event_id)
                continue
            if row_url and row_url == canonical_url(event.get("official_url", "")):
                assigned.add(event_id)
                continue
            if not published:
                continue
            start = _date(event["start_date"])
            end = _date(event["end_date"])
            if not start or not end:
                continue
            window_start = start - timedelta(days=45)
            window_end = end + timedelta(days=max(event.get("review_windows_days", [90])))
            if not window_start <= published <= window_end:
                continue
            aliases = [alias.casefold() for alias in event.get("aliases", []) if len(alias) >= 6]
            if any(alias in searchable for alias in aliases):
                assigned.add(event_id)
        if assigned:
            row["event_ids"] = sorted(assigned)
        else:
            row.pop("event_ids", None)

    # A second bounded pass links later records to inspectable event artifacts even
    # when the later source no longer names the conference or hackathon.
    anchors: dict[str, dict[str, set[str]]] = {
        event["id"]: {"urls": set(), "projects": set(), "titles": set()}
        for event in events
    }
    for row in rows:
        if not row.get("event_ids"):
            continue
        urls = {
            canonical_url(row.get("url", "")),
            *(canonical_url(url) for url in row.get("artifact_urls", [])),
        }
        projects = {compact_text(project).casefold() for project in row.get("projects", []) if compact_text(project)}
        title = compact_text(row.get("title", "")).casefold()
        for event_id in row["event_ids"]:
            if event_id not in anchors:
                continue
            anchors[event_id]["urls"].update(url for url in urls if url)
            anchors[event_id]["projects"].update(projects)
            if row.get("source_type") in ARTIFACT_TYPES and len(title) >= 6:
                anchors[event_id]["titles"].add(title)

    event_by_id = {event["id"]: event for event in events}
    for row in rows:
        published = _date(row.get("published_at", ""))
        if not published:
            continue
        row_url = canonical_url(row.get("url", ""))
        row_projects = {compact_text(project).casefold() for project in row.get("projects", []) if compact_text(project)}
        row_title = compact_text(row.get("title", "")).casefold()
        assigned = set(row.get("event_ids", []))
        for event_id, event_anchors in anchors.items():
            event = event_by_id[event_id]
            start = _date(event["start_date"])
            end = _date(event["end_date"])
            if not start or not end or not start <= published <= end + timedelta(days=max(event.get("review_windows_days", [90]))):
                continue
            artifact_match = bool(
                (row_url and row_url in event_anchors["urls"])
                or row_projects.intersection(event_anchors["projects"])
                or (len(row_title) >= 6 and row_title in event_anchors["titles"])
            )
            if artifact_match:
                assigned.add(event_id)
        if assigned:
            row["event_ids"] = sorted(assigned)
        else:
            row.pop("event_ids", None)
    return rows


def _echo_key(item: dict[str, Any]) -> str:
    artifact_urls = [canonical_url(url) for url in item.get("artifact_urls", []) if canonical_url(url)]
    if artifact_urls:
        return f"artifact:{artifact_urls[0]}"
    if item.get("source_type") in {"event-session", "event-paper", "hackathon-project", "curated-social"}:
        return f"title:{slugify(item.get('title', ''))}"
    url = canonical_url(item.get("url", ""))
    return f"url:{url}" if url else f"title:{slugify(item.get('title', ''))}"


def _score_label(value: int | None) -> str:
    if value is None:
        return "not-observed"
    if value >= 80:
        return "very-high"
    if value >= 60:
        return "high"
    if value >= 40:
        return "moderate"
    return "limited"


def _checkpoint(event: dict[str, Any], items: list[dict[str, Any]], days: int, as_of: datetime) -> dict[str, Any]:
    end = _date(event["end_date"])
    due = end + timedelta(days=days) if end else as_of
    if as_of < due:
        return {"days": days, "due_at": due.date().isoformat(), "status": "pending", "evidence_count": 0, "source_count": 0}
    official_sources = set(event.get("source_ids", []))
    later = [
        item for item in items
        if (published := _date(item.get("published_at", "")))
        and end < published <= due
        and item.get("source_id") not in official_sources
    ]
    sources = {item["source_id"] for item in later}
    status = "confirmed" if len(later) >= 3 and len(sources) >= 2 else "limited" if later else "not-observed"
    return {
        "days": days,
        "due_at": due.date().isoformat(),
        "status": status,
        "evidence_count": len(later),
        "source_count": len(sources),
        "evidence_ids": [item["id"] for item in later[:8]],
    }


def _event_finding(event: dict[str, Any], items: list[dict[str, Any]], themes: list[dict[str, Any]], source_count: int, artifact_count: int) -> str:
    if not items:
        return "No event-linked observations have been collected yet; the event remains configured rather than analyzed."
    top_names = [theme["name"] for theme in themes[:3]]
    focus = ", ".join(top_names) if top_names else "no stable taxonomy cluster yet"
    evidence_word = "artifact" if artifact_count == 1 else "artifacts"
    concentration = "one source" if source_count == 1 else f"{source_count} sources"
    return (
        f"The observed event record concentrates on {focus}. It contains {artifact_count} concrete {evidence_word} "
        f"across {concentration}; this establishes what appeared around the event, not whether it became adopted."
    )


def build_event_pulse(
    evidence: list[dict[str, Any]],
    config: dict[str, Any],
    source_defs: list[dict[str, Any]],
    theme_defs: list[dict[str, Any]],
    as_of: datetime | None = None,
) -> dict[str, Any]:
    validate_event_config(config)
    as_of = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    sources = {source["id"]: source for source in source_defs}
    theme_names = {theme["id"]: theme.get("name", theme["id"]) for theme in theme_defs}
    dossiers = []
    all_evidence_ids: set[str] = set()
    all_source_ids: set[str] = set()

    for event in config.get("events", []):
        items = [item for item in evidence if event["id"] in item.get("event_ids", [])]
        items.sort(key=lambda item: (item.get("published_at", ""), item["id"]), reverse=True)
        all_evidence_ids.update(item["id"] for item in items)
        all_source_ids.update(item["source_id"] for item in items)
        unique_keys = {_echo_key(item) for item in items}
        source_ids = sorted({item["source_id"] for item in items})
        family_ids = {
            sources.get(item["source_id"], {}).get("channel", item.get("source_type", "unknown"))
            for item in items
        }
        artifacts = [
            item for item in items
            if item.get("source_type") in ARTIFACT_TYPES or item.get("artifact_urls")
        ]
        artifact_types = {item.get("source_type") for item in artifacts}
        technical = [
            item for item in items
            if item.get("source_type") in ARTIFACT_TYPES
            or sources.get(item["source_id"], {}).get("channel") in TECHNICAL_CHANNELS
        ]
        theme_counts = Counter(theme_id for item in items for theme_id in item.get("theme_ids", []))
        themes = [
            {"id": theme_id, "name": theme_names.get(theme_id, theme_id), "evidence_count": count}
            for theme_id, count in sorted(theme_counts.items(), key=lambda pair: (-pair[1], pair[0]))
        ]
        checkpoints = [_checkpoint(event, items, days, as_of) for days in event.get("review_windows_days", [30, 90])]
        followthrough = max((checkpoint["evidence_count"] for checkpoint in checkpoints), default=0)

        if items:
            attention_components = {
                "volume_points": min(35, round(12 * math.log1p(len(unique_keys)))),
                "source_breadth_points": min(25, len(source_ids) * 8),
                "evidence_family_points": min(20, len(family_ids) * 5),
                "followthrough_points": min(20, followthrough * 5),
            }
            attention_score = sum(attention_components.values())
            technical_share = len(technical) / len(items)
            substance_components = {
                "artifact_points": min(35, round(12 * math.log1p(len(artifacts)))),
                "technical_share_points": round(25 * technical_share),
                "artifact_diversity_points": min(20, len(artifact_types) * 10),
                "independent_followthrough_points": min(20, followthrough * 5),
            }
            substance_score = sum(substance_components.values())
        else:
            attention_components = {"volume_points": 0, "source_breadth_points": 0, "evidence_family_points": 0, "followthrough_points": 0}
            substance_components = {"artifact_points": 0, "technical_share_points": 0, "artifact_diversity_points": 0, "independent_followthrough_points": 0}
            attention_score = None
            substance_score = None

        social_items = [item for item in items if item.get("source_type") == "curated-social"]
        record_counts = Counter(
            "artifact" if item in artifacts else "observation" if item.get("source_type") == "curated-social" else "claim"
            for item in items
        )
        dossiers.append(
            {
                **event,
                "analysis_status": "active" if items else "configured",
                "evidence_count": len(items),
                "independent_observation_count": len(unique_keys),
                "echo_records_collapsed": max(0, len(items) - len(unique_keys)),
                "source_ids": source_ids,
                "source_count": len(source_ids),
                "source_family_count": len(family_ids),
                "artifact_count": len(artifacts),
                "social_observation_count": len(social_items),
                "record_counts": dict(record_counts),
                "technical_record_count": len(technical),
                "narrative_record_count": len(items) - len(technical),
                "attention": {
                    "score": attention_score,
                    "label": _score_label(attention_score),
                    "components": attention_components,
                    "interpretation": "Observed event attention only; agenda size and social repetition do not establish quality or adoption.",
                },
                "technical_substance": {
                    "score": substance_score,
                    "label": _score_label(substance_score),
                    "components": substance_components,
                    "interpretation": "Concrete papers, projects, repositories, and independent follow-through drive this score; claims alone do not.",
                },
                "persistence_checks": checkpoints,
                "themes": themes[:8],
                "finding": _event_finding(event, items, themes, len(source_ids), len(artifacts)),
                "why_it_matters": event["framing"],
                "verification_read": (
                    "Technical artifacts are present, but event affiliation is not independent validation."
                    if artifacts else "Only event claims or observations are present; technical substance is not yet demonstrated."
                ),
                "next_confirmation": "Look for independent repositories, deployment reports, benchmarks, hiring demand, or repeated cross-source evidence after the event.",
                "counter_signal": "The concept disappears after the event, remains confined to sponsor language, or produces no inspectable artifact or later independent use.",
                "evidence_ids": [item["id"] for item in items],
                "artifact_evidence_ids": [item["id"] for item in artifacts[:12]],
                "social_evidence_ids": [item["id"] for item in social_items[:12]],
                "project_names": sorted({project for item in artifacts for project in item.get("projects", [])}),
            }
        )

    dossiers.sort(key=lambda item: (item["analysis_status"] != "active", -(item["attention"]["score"] or -1), item["name"]))
    active = [event for event in dossiers if event["analysis_status"] == "active"]
    social_count = sum(event["social_observation_count"] for event in dossiers)
    payload = {
        "meta": {
            "generated_at": as_of.isoformat(),
            "status": "active" if active else "configured",
            "event_count": len(dossiers),
            "active_event_count": len(active),
            "pilot_event_count": sum(bool(event.get("pilot")) for event in dossiers),
            "evidence_count": len(all_evidence_ids),
            "source_count": len(all_source_ids),
        },
        "analysis": {
            "id": "event-pulse",
            "title": "Event Pulse",
            "question": "Which ideas and engineering artifacts surface around AI conferences and hackathons—and which persist after the event echo fades?",
            "summary": "Event-linked programs, papers, projects, and selected public observations are analyzed as provenance contexts, with attention separated from technical substance and 30/90-day persistence checks.",
            "status": "active" if active else "configured",
            "source_ids": sorted(all_source_ids),
            "evidence_count": len(all_evidence_ids),
            "event_count": len(dossiers),
            "active_event_count": len(active),
            "executive_summary": (
                f"{len(active)} events currently have linked evidence. High event volume is not treated as corroboration: each dossier reports concrete artifacts, source concentration, and later independent follow-through separately."
                if active else "The event registry is configured, but no event-linked evidence has been collected yet."
            ),
            "events": dossiers,
            "social_inbox": {
                "status": "empty" if social_count == 0 else "active",
                "record_count": social_count,
                "accepted_platforms": config.get("social_inbox", {}).get("accepted_platforms", []),
                "submission_url": config.get("social_inbox", {}).get("submission_url", ""),
                "review_label": config.get("social_inbox", {}).get("review_label", ""),
                "instruction": "Add a public URL and an original observation to the reviewed social-link inbox; do not copy full post text.",
            },
            "method": config["policy"],
            "updated_at": as_of.isoformat(),
        },
    }
    return payload
