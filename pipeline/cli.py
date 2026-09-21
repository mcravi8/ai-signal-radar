from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .classify import classify_text
from .cluster import group_by_theme
from .deduplicate import deduplicate
from .export_public import validate_public_payload, write_public_dashboard
from .research import build_research, write_weekly_report
from .score import score_theme
from .storage import merge_items, read_jsonl, write_jsonl

ROOT = Path(__file__).resolve().parents[1]


def _yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def collect() -> None:
    from .collectors import arxiv, github, hackernews, huggingface, rss, sitemap

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

    snapshot = ROOT / "data/snapshots" / date.today().isoformat() / "items.jsonl"
    write_jsonl(snapshot, [item.to_dict() for item in collected])
    added = merge_items(ROOT / "data/processed/items.jsonl", collected)
    status = {"collected_at": datetime.now(timezone.utc).isoformat(), "items": len(collected), "added": added, "errors": errors}
    (snapshot.parent / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    if not collected and errors:
        raise SystemExit("All enabled collectors failed")


def synthesize() -> None:
    rows = deduplicate(read_jsonl(ROOT / "data/processed/items.jsonl"))
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

    public_items = []
    for row in rows:
        public_items.append({key: row[key] for key in (
            "id", "source_id", "source_type", "title", "url", "published_at", "summary", "authors", "tags", "projects", "sponsor_status", "theme_ids"
        ) if key in row})

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
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
            for source in _yaml(ROOT / "config/sources.yml")["sources"]
        ],
    }
    write_public_dashboard(ROOT / "data/public/dashboard.json", payload)

    alpha_path = ROOT / "data/public/alphasignal-research.json"
    if alpha_path.exists():
        alpha = json.loads(alpha_path.read_text(encoding="utf-8"))
        mappings = _yaml(ROOT / "config/source-theme-mappings.yml")
        research_input = {**payload, "evidence": public_items}
        research = build_research(research_input, alpha, taxonomy, mappings)
        write_public_dashboard(ROOT / "data/public/research.json", research)
        report_date = research["weekly"]["as_of"]
        write_weekly_report(ROOT / "reports/weekly" / f"{report_date}.md", research)
        print(
            f"research: {research['meta']['normalized_evidence_count']} normalized evidence records, "
            f"{research['meta']['observed_theme_count']} observed themes"
        )


def validate_public() -> None:
    for path in sorted((ROOT / "data/public").rglob("*.json")):
        validate_public_payload(json.loads(path.read_text(encoding="utf-8")))
        print(f"valid: {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-signal-radar")
    parser.add_argument("command", choices=["collect", "synthesize", "validate-public"])
    args = parser.parse_args()
    if args.command == "collect":
        collect()
    elif args.command == "synthesize":
        synthesize()
    else:
        validate_public()


if __name__ == "__main__":
    main()
