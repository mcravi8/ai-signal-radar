from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .classify import classify_text
from .cluster import group_by_theme
from .concepts import build_concept_catalog, validate_concept_policy
from .deduplicate import deduplicate
from .discovery import validate_discovery_policy
from .evidence_policy import build_operating_model, format_calibration, run_calibration
from .export_public import sanitize_item, validate_public_payload, write_public_dashboard
from .research import build_research, write_weekly_report
from .score import score_theme
from .storage import merge_items, read_jsonl, write_jsonl
from .weekly_review import build_weekly_review, write_weekly_review

ROOT = Path(__file__).resolve().parents[1]


def _yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def collect() -> None:
    from .collectors import arxiv, github, hackernews, huggingface, rss, sitemap, yc

    source_config = _yaml(ROOT / "config/sources.yml")["sources"]
    enabled = {source["id"]: source for source in source_config if source.get("enabled")}
    collected = []
    errors: list[str] = []

    def attempt(name: str, fn) -> None:
        try:
            rows = fn()
            collected.extend(rows)
            print(f"{name}: collected {len(rows)}")
        except Exception as exc:  # individual source failure must not erase other evidence
            errors.append(f"{name}: {exc}")
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

    snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "items.jsonl"
    write_jsonl(snapshot, [item.to_dict() for item in collected])
    added = merge_items(ROOT / "data/processed/items.jsonl", collected)
    status = {"collected_at": datetime.now(timezone.utc).isoformat(), "items": len(collected), "added": added, "errors": errors}
    (snapshot.parent / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    if not collected and errors:
        raise SystemExit("All enabled collectors failed")


def collect_verification() -> None:
    from .collectors import yc

    source_config = _yaml(ROOT / "config/sources.yml")["sources"]
    enabled = {source["id"]: source for source in source_config if source.get("enabled")}
    collected = []
    errors: list[str] = []
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
            print(f"{source_id}: collected {len(rows)}")
        except Exception as exc:
            errors.append(f"{source_id}: {exc}")
            print(f"{source_id}: failed: {exc}")

    sanitized = [sanitize_item(item.to_dict()) for item in collected]
    validate_public_payload({"items": sanitized})
    added = merge_items(ROOT / "data/processed/items.jsonl", collected)
    if sanitized:
        snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "verification-items.jsonl"
        write_jsonl(snapshot, sanitized)
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
    print(
        f"agentmail: saw {result.messages_seen} messages, matched {result.messages_matched}, "
        f"extracted {len(result.items)} sanitized records, added {added}"
    )


def collect_bluesky() -> None:
    from .collectors import bluesky

    result = bluesky.collect(_yaml(ROOT / "config/bluesky.yml"))
    sanitized = [sanitize_item(item.to_dict()) for item in result.items]
    validate_public_payload({"items": sanitized})
    added = merge_items(ROOT / "data/processed/items.jsonl", result.items)
    if sanitized:
        snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "bluesky-items.jsonl"
        write_jsonl(snapshot, sanitized)
    for error in result.errors:
        print(f"bluesky: partial failure: {error}")
    print(
        f"bluesky: collected {result.accounts_collected} accounts, "
        f"extracted {len(result.items)} relevant public posts, added {added}"
    )


def synthesize() -> None:
    discovery_policy = _yaml(ROOT / "config/discovery.yml")
    concept_policy = _yaml(ROOT / "config/discovery-concepts.yml")
    validate_discovery_policy(discovery_policy)
    validate_concept_policy(concept_policy)
    generated_at = datetime.now(timezone.utc)
    manual_rows = _yaml(ROOT / "data/manual/items.yml").get("items", [])
    rows = deduplicate([*read_jsonl(ROOT / "data/processed/items.jsonl"), *manual_rows])
    keywords = _yaml(ROOT / "config/keywords.yml").get("themes", {})
    taxonomy = _yaml(ROOT / "config/taxonomy.yml")
    theme_defs = {theme["id"]: theme for theme in taxonomy.get("seed_themes", [])}

    for row in rows:
        searchable = " ".join([row.get("title", ""), row.get("summary", ""), " ".join(row.get("tags", []))])
        row["theme_ids"] = classify_text(searchable, keywords)

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
    concept_path = ROOT / "data/processed/discovery-concepts.json"
    previous_concepts = json.loads(concept_path.read_text(encoding="utf-8")) if concept_path.exists() else None
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
    write_public_dashboard(concept_path, concept_catalog)

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
        )
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
    print("valid: config/discovery.yml")
    print("valid: config/discovery-concepts.yml")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-signal-radar")
    parser.add_argument(
        "command",
        choices=["collect", "collect-verification", "collect-bluesky", "collect-newsletters", "synthesize", "validate-public", "calibrate-evidence", "validate-discovery"],
    )
    args = parser.parse_args()
    if args.command == "collect":
        collect()
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
    else:
        validate_public()


if __name__ == "__main__":
    main()
