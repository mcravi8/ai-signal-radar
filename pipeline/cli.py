from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .classify import classify_record, validate_classification_policy
from .cluster import group_by_theme
from .collection_health import build_collection_health
from .concepts import build_concept_catalog, validate_concept_policy
from .deduplicate import deduplicate
from .discovery import validate_discovery_policy
from .discovery_cluster import build_discovery_candidates, validate_clustering_policy
from .evidence_policy import build_operating_model, format_calibration, run_calibration
from .events import assign_event_ids, build_event_pulse, load_social_links, validate_event_config
from .export_public import sanitize_item, validate_public_payload, write_public_dashboard
from .research import EARLY_SIGNAL_DIRECTIONS, build_research, write_weekly_report
from .score import score_theme
from .storage import merge_items, read_jsonl, write_jsonl
from .weekly_review import build_weekly_review, write_weekly_review

ROOT = Path(__file__).resolve().parents[1]


def _yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def collect() -> None:
    from .collectors import arxiv, events, github, hackernews, huggingface, rss, sitemap, yc

    source_config = _yaml(ROOT / "config/sources.yml")["sources"]
    enabled = {source["id"]: source for source in source_config if source.get("enabled")}
    collected = []
    errors: list[str] = []
    collectors: list[dict] = []

    def attempt(name: str, fn, source_ids: list[str] | None = None) -> None:
        expected = source_ids or [name]
        try:
            rows = fn()
            collected.extend(rows)
            counts = Counter(item.source_id for item in rows)
            collectors.extend(
                {"source_id": source_id, "status": "healthy", "items": counts[source_id]}
                for source_id in expected
            )
            print(f"{name}: collected {len(rows)}")
        except Exception as exc:  # individual source failure must not erase other evidence
            errors.append(f"{name}: {exc}")
            collectors.extend(
                {"source_id": source_id, "status": "failed", "items": 0, "error": str(exc)}
                for source_id in expected
            )
            print(f"{name}: failed: {exc}")

    if "arxiv" in enabled:
        attempt("arxiv", lambda: arxiv.collect(enabled["arxiv"]["categories"]))
    if "huggingface-papers" in enabled:
        attempt("huggingface-papers", lambda: huggingface.collect(enabled["huggingface-papers"].get("limit", 50)))
    if "github" in enabled:
        queries = _yaml(ROOT / "config/github-queries.yml")["queries"]
        since = (date.today() - timedelta(days=30)).isoformat()
        attempt("github", lambda: github.collect(queries, since))
    if "hacker-news" in enabled:
        attempt("hacker-news", lambda: hackernews.collect(enabled["hacker-news"]["feeds"]))
    if {"linkedin-event-links", "x-event-links"}.intersection(enabled):
        event_config = _yaml(ROOT / "config/events.yml")
        attempt(
            "reviewed-social-inbox",
            lambda: events.collect_reviewed_social_issues(
                os.getenv("GITHUB_REPOSITORY", "mcravi8/ai-signal-radar"),
                os.getenv("AI_RADAR_GITHUB_TOKEN", ""),
                event_config,
            ),
            ["linkedin-event-links", "x-event-links"],
        )
    for source_id, source in enabled.items():
        if source.get("collection") == "rss":
            attempt(
                source_id,
                lambda source_id=source_id, source=source: rss.collect(
                    source_id,
                    source.get("channel", "essay"),
                    source["feed_url"],
                    source.get("limit", 30),
                ),
            )
        elif source.get("collection") == "sitemap":
            attempt(
                source_id,
                lambda source_id=source_id, source=source: sitemap.collect(
                    source_id,
                    source.get("channel", "first-party-lab"),
                    source["sitemap_url"],
                    source.get("include_prefixes", []),
                    source.get("limit", 30),
                    source.get("include_patterns", []),
                ),
            )
        elif source.get("collection") == "yc-directory":
            attempt(
                source_id,
                lambda source=source: yc.collect_companies(source["directory_url"], source.get("limit", 50)),
            )
        elif source.get("collection") == "yc-jobs":
            attempt(
                source_id,
                lambda source=source: yc.collect_jobs(source["jobs_url"], source.get("terms", []), source.get("limit", 50)),
            )
        elif source.get("collection") in {"event-json", "conference-proceedings", "devpost-gallery"}:
            attempt(source_id, lambda source=source: events.collect_source(source))

    snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "items.jsonl"
    write_jsonl(snapshot, [item.to_dict() for item in collected])
    added = merge_items(ROOT / "data/processed/items.jsonl", collected)
    status = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "items": len(collected),
        "added": added,
        "errors": errors,
        "collectors": collectors,
    }
    (snapshot.parent / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    if not collected and errors:
        raise SystemExit("All enabled collectors failed")


def collect_events() -> None:
    from .collectors import events

    source_config = _yaml(ROOT / "config/sources.yml")["sources"]
    event_sources = [
        source for source in source_config
        if source.get("enabled") and source.get("collection") in {"event-json", "conference-proceedings", "devpost-gallery"}
    ]
    collected = []
    errors: list[str] = []
    collectors: list[dict] = []
    for source in event_sources:
        try:
            rows = events.collect_source(source)
            collected.extend(rows)
            collectors.append({"source_id": source["id"], "status": "healthy", "items": len(rows)})
            print(f"{source['id']}: collected {len(rows)}")
        except Exception as exc:
            errors.append(f"{source['id']}: {exc}")
            collectors.append({"source_id": source["id"], "status": "failed", "items": 0, "error": str(exc)})
            print(f"{source['id']}: failed: {exc}")
    try:
        social_rows = events.collect_reviewed_social_issues(
            os.getenv("GITHUB_REPOSITORY", "mcravi8/ai-signal-radar"),
            os.getenv("AI_RADAR_GITHUB_TOKEN", ""),
            _yaml(ROOT / "config/events.yml"),
        )
        collected.extend(social_rows)
        social_counts = Counter(item.source_id for item in social_rows)
        collectors.extend(
            {"source_id": source_id, "status": "healthy", "items": social_counts[source_id]}
            for source_id in ("linkedin-event-links", "x-event-links")
        )
        print(f"reviewed-social-inbox: collected {len(social_rows)}")
    except Exception as exc:
        errors.append(f"reviewed-social-inbox: {exc}")
        collectors.extend(
            {"source_id": source_id, "status": "failed", "items": 0, "error": str(exc)}
            for source_id in ("linkedin-event-links", "x-event-links")
        )
        print(f"reviewed-social-inbox: failed: {exc}")
    sanitized = [sanitize_item(item.to_dict()) for item in collected]
    validate_public_payload({"items": sanitized})
    added = merge_items(ROOT / "data/processed/items.jsonl", collected)
    snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "event-items.jsonl"
    write_jsonl(snapshot, sanitized)
    status = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "items": len(collected),
        "added": added,
        "errors": errors,
        "collectors": collectors,
    }
    (snapshot.parent / "event-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(f"events: extracted {len(collected)} public records, added {added}")
    if not collected and errors:
        raise SystemExit("All event collectors failed")


def collect_verification() -> None:
    from .collectors import yc

    source_config = _yaml(ROOT / "config/sources.yml")["sources"]
    enabled = {source["id"]: source for source in source_config if source.get("enabled")}
    collected = []
    errors: list[str] = []
    collectors: list[dict] = []
    for source_id in ("yc-companies", "yc-jobs"):
        source = enabled.get(source_id)
        if not source:
            continue
        try:
            if source_id == "yc-companies":
                rows = yc.collect_companies(source["directory_url"], source.get("limit", 50))
            else:
                rows = yc.collect_jobs(source["jobs_url"], source.get("terms", []), source.get("limit", 50))
            collected.extend(rows)
            collectors.append({"source_id": source_id, "status": "healthy", "items": len(rows)})
            print(f"{source_id}: collected {len(rows)}")
        except Exception as exc:
            errors.append(f"{source_id}: {exc}")
            collectors.append({"source_id": source_id, "status": "failed", "items": 0, "error": str(exc)})
            print(f"{source_id}: failed: {exc}")

    sanitized = [sanitize_item(item.to_dict()) for item in collected]
    validate_public_payload({"items": sanitized})
    added = merge_items(ROOT / "data/processed/items.jsonl", collected)
    if sanitized:
        snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "verification-items.jsonl"
        write_jsonl(snapshot, sanitized)
    status_path = ROOT / "data/snapshots" / date.today().isoformat() / "verification-status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps({
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "items": len(collected),
        "added": added,
        "errors": errors,
        "collectors": collectors,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"verification: extracted {len(collected)} public records, added {added}")
    if not collected and errors:
        raise SystemExit("All verification collectors failed")


def collect_newsletters() -> None:
    from .collectors import agentmail

    api_key = os.getenv("AGENTMAIL_API_KEY", "").strip()
    require_agentmail = os.getenv("AI_RADAR_REQUIRE_AGENTMAIL") == "1"
    if not api_key:
        if require_agentmail:
            raise SystemExit("AGENTMAIL_API_KEY is required for newsletter ingestion")
        print("agentmail: skipped (AGENTMAIL_API_KEY is not configured)")
        return

    inbox_id = os.getenv("AGENTMAIL_INBOX_ID", "ai-signal-radar@agentmail.to").strip()
    cursor_path = ROOT / "data/state/agentmail.json"
    after = agentmail.read_after(cursor_path)
    definitions = agentmail.load_definitions(ROOT / "config/newsletters.yml")
    result = agentmail.collect(api_key, inbox_id, definitions, after=after)

    sanitized = [sanitize_item(item.to_dict()) for item in result.items]
    validate_public_payload({"items": sanitized})
    added = merge_items(ROOT / "data/processed/items.jsonl", result.items)
    if sanitized:
        snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "newsletter-items.jsonl"
        write_jsonl(snapshot, sanitized)

    if result.next_after and result.next_after != after:
        agentmail.write_after(cursor_path, result.next_after)
    counts = Counter(item.source_id for item in result.items)
    status_path = ROOT / "data/snapshots" / date.today().isoformat() / "newsletter-status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps({
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "items": len(result.items),
        "added": added,
        "errors": [],
        "collectors": [
            {"source_id": definition.source_id, "status": "healthy", "items": counts[definition.source_id]}
            for definition in definitions
        ],
    }, indent=2) + "\n", encoding="utf-8")
    print(
        f"agentmail: saw {result.messages_seen} messages, matched {result.messages_matched}, "
        f"extracted {len(result.items)} sanitized records, added {added}"
    )


def collect_bluesky() -> None:
    from .collectors import bluesky

    config = _yaml(ROOT / "config/bluesky.yml")
    result = bluesky.collect(config)
    sanitized = [sanitize_item(item.to_dict()) for item in result.items]
    validate_public_payload({"items": sanitized})
    added = merge_items(ROOT / "data/processed/items.jsonl", result.items)
    if sanitized:
        snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "bluesky-items.jsonl"
        write_jsonl(snapshot, sanitized)
    for error in result.errors:
        print(f"bluesky: partial failure: {error}")
    counts = Counter(item.source_id for item in result.items)
    errors_by_handle = {str(error).partition(":")[0]: str(error).partition(":")[2].strip() for error in result.errors}
    status_path = ROOT / "data/snapshots" / date.today().isoformat() / "bluesky-status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps({
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "items": len(result.items),
        "added": added,
        "errors": result.errors,
        "collectors": [
            {
                "source_id": account["source_id"],
                "status": "failed" if account["handle"] in errors_by_handle else "healthy",
                "items": counts[account["source_id"]],
                **({"error": errors_by_handle[account["handle"]]} if account["handle"] in errors_by_handle else {}),
            }
            for account in config.get("accounts", [])
        ],
    }, indent=2) + "\n", encoding="utf-8")
    print(
        f"bluesky: collected {result.accounts_collected} accounts, "
        f"extracted {len(result.items)} relevant public posts, added {added}"
    )


def synthesize() -> None:
    discovery_policy = _yaml(ROOT / "config/discovery.yml")
    concept_policy = _yaml(ROOT / "config/discovery-concepts.yml")
    clustering_policy = _yaml(ROOT / "config/discovery-clustering.yml")
    validate_discovery_policy(discovery_policy)
    validate_concept_policy(concept_policy)
    validate_clustering_policy(clustering_policy)
    event_config = _yaml(ROOT / "config/events.yml")
    validate_event_config(event_config)
    generated_at = datetime.now(timezone.utc)
    manual_rows = _yaml(ROOT / "data/manual/items.yml").get("items", [])
    social_rows = [
        item.to_dict()
        for item in load_social_links(_yaml(ROOT / "data/manual/social-links.yml"), event_config)
    ]
    processed_rows = read_jsonl(ROOT / "data/processed/items.jsonl")
    processed_by_id = {row["id"]: row for row in processed_rows}
    # Reviewed manual records are authoritative when an automated collector has
    # already stored the same URL/title with sparse metadata (for example, a
    # GitHub repository whose API description is empty). Fresh collector
    # metadata still wins so repository metrics can continue to update.
    reviewed_rows = [
        {
            **processed_by_id.get(row["id"], {}),
            **row,
            "metadata": {
                **row.get("metadata", {}),
                **processed_by_id.get(row["id"], {}).get("metadata", {}),
            },
        }
        for row in manual_rows
    ]
    rows = deduplicate([*reviewed_rows, *social_rows, *processed_rows])
    assign_event_ids(rows, event_config)
    keywords = _yaml(ROOT / "config/keywords.yml").get("themes", {})
    classification_policy = _yaml(ROOT / "config/classification-policy.yml")
    validate_classification_policy(classification_policy)
    taxonomy = _yaml(ROOT / "config/taxonomy.yml")
    theme_defs = {theme["id"]: theme for theme in taxonomy.get("seed_themes", [])}

    for row in rows:
        classification = classify_record(row, keywords, classification_policy)
        row["theme_ids"] = classification["theme_ids"]
        row["classification_disposition"] = classification["disposition"]
        row["classification_reason"] = classification["reason"]
        row["classification_rule_id"] = classification["rule_id"]

    rows.sort(key=lambda row: (row.get("published_at", ""), row["id"]))
    write_jsonl(ROOT / "data/processed/items.jsonl", rows)
    grouped = group_by_theme(rows)
    themes = []
    for theme_id, definition in theme_defs.items():
        evidence = grouped.get(theme_id, [])
        source_types = sorted({row.get("source_type", "unknown") for row in evidence})
        themes.append(
            {
                **definition,
                "definition": definition.get("definition", "Seed theme; definition will be refined from evidence."),
                "maturity": "watchlist" if len(evidence) < 3 else "emerging",
                "evidence_count": len(evidence),
                "source_types": source_types,
                "score": score_theme(evidence).to_dict() if evidence else None,
            }
        )

    public_items = [sanitize_item(row) for row in rows]
    source_config = _yaml(ROOT / "config/sources.yml")["sources"]
    collection_health = build_collection_health(ROOT / "data/snapshots", source_config)
    concept_path = ROOT / "data/processed/discovery-concepts.json"
    candidate_path = ROOT / "data/processed/discovery-candidates.json"
    previous_concepts = json.loads(concept_path.read_text(encoding="utf-8")) if concept_path.exists() else None
    previous_candidates = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path.exists() else None
    previous_baseline_version = (previous_candidates or {}).get("meta", {}).get("baseline_version")
    discovery_baseline = previous_baseline_version != clustering_policy["version"]
    concept_catalog = build_concept_catalog(
        public_items,
        source_config,
        discovery_policy,
        taxonomy,
        {"themes": keywords},
        concept_policy,
        as_of=generated_at,
        previous_catalog=previous_concepts,
    )
    if discovery_baseline:
        concept_catalog["changed_document_ids"] = sorted(
            document["evidence_id"] for document in concept_catalog.get("documents", [])
        )
        concept_catalog["meta"]["changed_document_count"] = len(concept_catalog["changed_document_ids"])
    write_public_dashboard(concept_path, concept_catalog)
    discovery_candidates = build_discovery_candidates(
        concept_catalog,
        source_config,
        discovery_policy,
        taxonomy,
        EARLY_SIGNAL_DIRECTIONS,
        clustering_policy,
    )
    discovery_candidates["meta"]["baseline_cycle"] = discovery_baseline
    discovery_candidates["meta"]["baseline_complete"] = True
    discovery_candidates["meta"]["baseline_version"] = clustering_policy["version"]
    write_public_dashboard(candidate_path, discovery_candidates)
    discovery_review = {
        "meta": discovery_candidates["meta"],
        "records": discovery_candidates["records"],
        "merge_suggestions": discovery_candidates["merge_suggestions"],
        "history": [
            record
            for record in discovery_candidates["records"]
            if record.get("state") in {"rejected", "dormant"}
        ],
    }
    write_public_dashboard(ROOT / "data/public/discovery-review.json", discovery_review)

    payload = {
        "meta": {
            "generated_at": generated_at.isoformat(),
            "status": "success" if rows else "empty",
            "source_count": len({row.get("source_id") for row in rows}),
            "evidence_count": len(rows),
            "warnings": [],
        },
        "weekly": {
            "title": "Weekly AI signal brief",
            "summary": "Cross-source evidence is grouped into inspectable themes. Open a theme to review the underlying public sources.",
            "signals": [theme["id"] for theme in sorted(themes, key=lambda item: item.get("evidence_count", 0), reverse=True)[:5]],
        },
        "themes": themes,
        "evidence": public_items[-250:],
        "projects": [],
        "sources": [
            {key: source[key] for key in ("id", "name", "channel", "source_quality", "commercial_bias", "publisher_id", "evidence_role", "homepage_url", "logo_url") if key in source}
            for source in source_config
        ],
    }
    write_public_dashboard(ROOT / "data/public/dashboard.json", payload)

    alpha_path = ROOT / "data/public/alphasignal-research.json"
    if alpha_path.exists():
        alpha = json.loads(alpha_path.read_text(encoding="utf-8"))
        mappings = _yaml(ROOT / "config/source-theme-mappings.yml")
        project_reviews = _yaml(ROOT / "config/project-reviews.yml").get("reviews", {})
        classification_audit = _yaml(ROOT / "config/classification-audit.yml").get("audit", {})
        research_input = {**payload, "evidence": public_items}
        research = build_research(
            research_input,
            alpha,
            taxonomy,
            mappings,
            project_reviews,
            classification_audit,
            collection_health,
        )
        event_pulse = build_event_pulse(
            research["evidence"],
            event_config,
            research["sources"],
            taxonomy.get("seed_themes", []),
            as_of=generated_at,
        )
        research["analyses"].insert(4, event_pulse["analysis"])
        research["meta"]["event_count"] = event_pulse["meta"]["event_count"]
        research["meta"]["active_event_count"] = event_pulse["meta"]["active_event_count"]
        research["methodology"]["limits"].append(
            "Event programs, talks, projects, and social observations establish event context. Event attention, technical substance, and post-event persistence remain separate measures."
        )
        write_public_dashboard(ROOT / "data/public/event-pulse.json", event_pulse)
        write_public_dashboard(ROOT / "data/public/research.json", research)
        policy = _yaml(ROOT / "config/evidence-policy.yml")
        calibration = _yaml(ROOT / "config/evidence-policy-calibration.yml")
        operating_path = ROOT / "data/public/operating-model.json"
        weekly_review_path = ROOT / "data/public/weekly-review.json"
        previous_operating_model = json.loads(operating_path.read_text(encoding="utf-8")) if operating_path.exists() else None
        previous_weekly_review = json.loads(weekly_review_path.read_text(encoding="utf-8")) if weekly_review_path.exists() else None
        operating_model = build_operating_model(policy, calibration, research)
        write_public_dashboard(operating_path, operating_model)
        weekly_review = build_weekly_review(
            research,
            operating_model,
            previous_operating_model,
            previous_weekly_review,
            _yaml(ROOT / "config/weekly-review.yml"),
        )
        write_public_dashboard(weekly_review_path, weekly_review)
        report_date = research["weekly"]["as_of"]
        write_weekly_report(ROOT / "reports/weekly" / f"{report_date}.md", research)
        write_weekly_review(ROOT / "reports/weekly" / f"{report_date}-operating-model.md", weekly_review)
        print(
            f"research: {research['meta']['normalized_evidence_count']} normalized evidence records, "
            f"{research['meta']['observed_theme_count']} observed themes"
        )


def validate_public() -> None:
    for path in sorted((ROOT / "data/public").rglob("*.json")):
        validate_public_payload(json.loads(path.read_text(encoding="utf-8")))
        print(f"valid: {path.relative_to(ROOT)}")


def calibrate_evidence() -> None:
    policy = _yaml(ROOT / "config/evidence-policy.yml")
    calibration = _yaml(ROOT / "config/evidence-policy-calibration.yml")
    research = json.loads((ROOT / calibration["dataset"]).read_text(encoding="utf-8"))
    results = run_calibration(policy, calibration, research)
    print(format_calibration(results))
    mismatches = [result for result in results if not result["matches_expected"]]
    if mismatches:
        raise SystemExit("Evidence-policy calibration did not match the reviewed outcomes")


def validate_discovery() -> None:
    validate_discovery_policy(_yaml(ROOT / "config/discovery.yml"))
    validate_concept_policy(_yaml(ROOT / "config/discovery-concepts.yml"))
    validate_clustering_policy(_yaml(ROOT / "config/discovery-clustering.yml"))
    print("valid: config/discovery.yml")
    print("valid: config/discovery-concepts.yml")
    print("valid: config/discovery-clustering.yml")


def validate_events() -> None:
    config = _yaml(ROOT / "config/events.yml")
    validate_event_config(config)
    load_social_links(_yaml(ROOT / "data/manual/social-links.yml"), config)
    print("valid: config/events.yml")
    print("valid: data/manual/social-links.yml")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-signal-radar")
    parser.add_argument(
        "command",
        choices=["collect", "collect-events", "collect-verification", "collect-bluesky", "collect-newsletters", "synthesize", "validate-public", "calibrate-evidence", "validate-discovery", "validate-events"],
    )
    args = parser.parse_args()
    if args.command == "collect":
        collect()
    elif args.command == "collect-events":
        collect_events()
    elif args.command == "collect-verification":
        collect_verification()
    elif args.command == "collect-bluesky":
        collect_bluesky()
    elif args.command == "collect-newsletters":
        collect_newsletters()
    elif args.command == "synthesize":
        synthesize()
    elif args.command == "calibrate-evidence":
        calibrate_evidence()
    elif args.command == "validate-discovery":
        validate_discovery()
    elif args.command == "validate-events":
        validate_events()
    else:
        validate_public()


if __name__ == "__main__":
    main()
