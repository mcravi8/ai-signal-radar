from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .normalize import canonical_url, slugify


LAYER_IDS = {
    "Models & capabilities": "models-capabilities",
    "Harness & orchestration": "harness-orchestration",
    "Tools, skills & integrations": "tools-skills-integrations",
    "Assurance layer": "assurance",
}


EARLY_SIGNAL_DIRECTIONS = [
    {
        "id": "modular-agent-stack",
        "domain": "Agent engineering",
        "title": "The agent stack is separating into modular operating layers",
        "hypothesis": "Models are becoming replaceable components inside a larger system of harnesses, reusable skills, execution environments, and assurance controls.",
        "theme_ids": {"agent-harnesses", "skills-integrations", "assurance-infrastructure"},
        "interpretation": "Independent work is accumulating above the model API: orchestration controls execution, skills package repeatable actions, and assurance governs whether those actions can be trusted.",
        "why_it_matters": "Value and defensibility may shift from exclusive model access toward the infrastructure that makes changing models reliable inside real workflows.",
        "next_confirmation": "More production systems publishing interchangeable model adapters, portable skill interfaces, and assurance telemetry as separate components.",
        "counter_signal": "Application stacks continue to remain tightly coupled to one model vendor, with little reuse across runtimes or tools.",
    },
    {
        "id": "workflow-ownership",
        "domain": "Product architecture",
        "title": "AI products are moving from assistance toward bounded workflow ownership",
        "hypothesis": "The important product boundary is shifting from generating an answer to carrying a well-defined task from trigger to verified outcome.",
        "theme_ids": {"agent-harnesses", "enterprise-vertical-ai", "ai-native-gtm"},
        "interpretation": "Operator language around systems of action, AI workforces, and vertical agents points toward products measured by completed work and exception handling rather than chat quality.",
        "why_it_matters": "This creates room for products that own narrow operational loops, integrate with systems of record, and charge against measurable outcomes.",
        "next_confirmation": "Case studies reporting cycle-time, intervention-rate, or business-outcome improvements from agents operating a complete workflow.",
        "counter_signal": "Most deployments remain drafting tools that require people to coordinate every handoff and execute every consequential action.",
    },
    {
        "id": "heterogeneous-inference",
        "domain": "Inference architecture",
        "title": "Heterogeneous model portfolios are becoming the default inference architecture",
        "hypothesis": "Teams will combine frontier, small, open, local, and specialized models through routing and purpose-built serving rather than standardizing on one endpoint.",
        "theme_ids": {"small-specialized-models", "model-routing", "open-local-inference", "frontier-inference-infrastructure", "specialized-inference-silicon"},
        "interpretation": "Cost, latency, privacy, and task fit are becoming first-class architectural constraints. The emerging control plane chooses the model and runtime per request instead of treating inference as homogeneous.",
        "why_it_matters": "Routing, evaluation, caching, capacity planning, and fallback logic can become durable infrastructure even as the best individual model changes.",
        "next_confirmation": "Production benchmarks showing sustained quality and unit-economic gains from routing across model sizes, vendors, or specialized inference hardware.",
        "counter_signal": "Frontier APIs become cheap, fast, private, and reliable enough that routing complexity produces little operational benefit.",
    },
    {
        "id": "operational-context",
        "domain": "Enterprise systems",
        "title": "Enterprise context is evolving from document retrieval into an operational ontology",
        "hypothesis": "Agents need governed business objects, relationships, permissions, and actions—not only retrieved text—to operate reliably inside companies.",
        "theme_ids": {"operational-ontology", "memory-context", "document-knowledge-systems", "enterprise-vertical-ai"},
        "interpretation": "Memory and retrieval solve what the system can recall. Operational ontologies extend that layer with shared meanings, live state, rules, and allowed actions across systems of record.",
        "why_it_matters": "The enabling product may be a semantic control layer that lets many agents understand and manipulate the same organization without rebuilding context for every workflow.",
        "next_confirmation": "Open schemas, context graphs, or enterprise platforms demonstrating permission-aware actions across several business systems and agent vendors.",
        "counter_signal": "Workflow-specific retrieval and direct SaaS integrations remain sufficient, making a shared semantic layer too costly to maintain.",
    },
    {
        "id": "validation-as-release",
        "domain": "Assurance engineering",
        "title": "Validation is becoming the release gate for AI-generated work",
        "hypothesis": "As agents produce code and operational changes, evaluation, observability, security, and reversible deployment become one continuous release discipline.",
        "theme_ids": {"assurance-infrastructure", "validation-release", "training-self-improvement", "coding-agents"},
        "interpretation": "The bottleneck is moving from whether an agent can produce an output to whether the system can test, constrain, trace, and safely ship that output under real conditions.",
        "why_it_matters": "A reusable release layer could govern many agent workflows and become more durable than any individual agent interface.",
        "next_confirmation": "Teams publishing intervention rates, rollback data, policy violations, and production-quality evals as standard agent deployment metrics.",
        "counter_signal": "Model reliability improves enough that conventional testing and access control absorb agent-specific assurance requirements.",
    },
    {
        "id": "simulation-first-physical-ai",
        "domain": "Physical AI",
        "title": "Simulation is becoming the development environment for physical AI",
        "hypothesis": "World models, synthetic environments, and evaluation loops will mature before broadly deployed autonomous physical systems.",
        "theme_ids": {"robotics-embodied-ai", "multimodal-3d", "assurance-infrastructure"},
        "interpretation": "Research and investor narratives increasingly connect spatial models with scalable training and validation environments, where rare failures can be generated and replayed before physical deployment.",
        "why_it_matters": "Simulation, data generation, and safety evaluation may be nearer-term infrastructure opportunities than betting on one general-purpose robot application.",
        "next_confirmation": "Evidence that simulation-generated experience transfers reliably into deployed systems and materially reduces physical testing cost or failure rates.",
        "counter_signal": "Sim-to-real transfer remains weak enough that domain-specific physical data collection continues to dominate progress.",
    },
]


SOURCE_FAMILIES = {
    "first-party-lab": ("builders", "First-party builders"),
    "paper": ("research", "Research"),
    "paper-curation": ("research", "Research"),
    "repository": ("engineering", "Open engineering"),
    "expert-social": ("experts", "Expert interpretation"),
    "expert-newsletter": ("experts", "Expert interpretation"),
    "practitioner-blog": ("experts", "Expert interpretation"),
    "operator-essay": ("narratives", "Operator & capital narratives"),
    "investor-essay": ("narratives", "Operator & capital narratives"),
    "community": ("attention", "Market attention"),
    "newsletter": ("attention", "Market attention"),
    "curated-newsletter": ("attention", "Market attention"),
}


def _parse_date(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _month(value: str) -> str:
    parsed = _parse_date(value)
    return f"{parsed.year:04d}-{parsed.month:02d}" if parsed else ""


def _last_months(as_of: datetime, count: int = 6) -> list[str]:
    months = []
    year, month = as_of.year, as_of.month
    for offset in reversed(range(count)):
        absolute = year * 12 + month - 1 - offset
        months.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
    return months


def _stack_layers(theme_ids: list[str], themes: dict[str, dict[str, Any]]) -> list[str]:
    layers: list[str] = []
    for theme_id in theme_ids:
        theme = themes.get(theme_id, {})
        for key in ("primary_layer", "secondary_layer"):
            layer = theme.get(key)
            if layer and layer not in layers:
                layers.append(layer)
    return layers


def _normalize_public_evidence(row: dict[str, Any], themes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    month = _month(row.get("published_at", ""))
    theme_ids = row.get("theme_ids", [])
    return {
        "id": row["id"],
        "source_id": row.get("source_id", "unknown"),
        "source_type": row.get("source_type", "unknown"),
        "evidence_kind": "public-source-item",
        "title": row.get("title", "Untitled evidence"),
        "summary": row.get("summary", ""),
        "url": row.get("url", ""),
        "published_at": row.get("published_at", ""),
        "authors": row.get("authors", []),
        "projects": row.get("projects", []),
        "theme_ids": theme_ids,
        "disposition": "classified" if theme_ids else "classification-review",
        "stack_layers": _stack_layers(theme_ids, themes),
        "support_count": 1,
        "monthly_counts": {month: 1} if month else {},
        "provenance": {
            "mode": "direct-public-metadata",
            "description": "Normalized from the linked public source.",
        },
    }


def _normalize_alpha_evidence(
    alpha: dict[str, Any],
    themes: dict[str, dict[str, Any]],
    mappings: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    evidence: list[dict[str, Any]] = []
    project_evidence_ids: dict[str, str] = {}
    trend_map = mappings.get("alphasignal_trends", {})
    project_map = mappings.get("alphasignal_project_categories", {})

    for trend in alpha.get("trends", []):
        theme_ids = trend_map.get(trend["name"], [])
        evidence.append(
            {
                "id": f"alphasignal:trend:{slugify(trend['name'])}",
                "source_id": "alphasignal",
                "source_type": "newsletter-analysis",
                "evidence_kind": "aggregate-analysis",
                "title": trend["name"],
                "summary": trend["finding"],
                "url": "",
                "published_at": alpha["meta"]["analysis_date"],
                "authors": [],
                "projects": trend.get("examples", []),
                "theme_ids": theme_ids,
                "disposition": "classified" if theme_ids else "classification-review",
                "stack_layers": _stack_layers(theme_ids, themes),
                "support_count": trend["mentions"],
                "monthly_counts": trend.get("monthly_mentions", {}),
                "metrics": {
                    "mentions": trend["mentions"],
                    "trend_score": trend["score"]["total"],
                    "tier": trend["score"]["tier"],
                },
                "provenance": {
                    "mode": "private-corpus-aggregate",
                    "description": "Derived from the sanitized AlphaSignal corpus analysis; no raw email content is published.",
                    "underlying_corpus_records": alpha["meta"]["unique_catalog_records"],
                },
            }
        )

    for project in alpha.get("projects", []):
        theme_ids = project_map.get(project["category"], [])
        evidence_id = f"alphasignal:project:{slugify(project['name'])}"
        project_evidence_ids[project["name"]] = evidence_id
        month = _month(project.get("source_date", ""))
        evidence.append(
            {
                "id": evidence_id,
                "source_id": "alphasignal",
                "source_type": "newsletter-analysis",
                "evidence_kind": "project-assessment",
                "title": project["name"],
                "summary": project["why_it_matters"],
                "url": project.get("official_url", ""),
                "published_at": project.get("source_date", ""),
                "authors": [],
                "projects": [project["name"]],
                "theme_ids": theme_ids,
                "disposition": "classified" if theme_ids else "classification-review",
                "stack_layers": _stack_layers(theme_ids, themes),
                "support_count": 1,
                "monthly_counts": {month: 1} if month else {},
                "metrics": {
                    "opportunity_score": project["opportunity_score"],
                    "action": project["action"],
                    "hype_risk": project["hype_risk"],
                },
                "provenance": {
                    "mode": "private-corpus-assessment",
                    "description": "Analyst assessment derived from AlphaSignal discovery and linked to the project's official public page.",
                },
            }
        )
    return evidence, project_evidence_ids


def _movement(recent: int, prior: int) -> str:
    if recent == 0 and prior == 0:
        return "inactive"
    if recent > 0 and prior == 0:
        return "new"
    if recent >= prior * 1.5:
        return "rising"
    if prior >= recent * 1.5:
        return "falling"
    return "steady"


def _theme_analyses(
    evidence: list[dict[str, Any]],
    theme_defs: list[dict[str, Any]],
    as_of: datetime,
) -> list[dict[str, Any]]:
    months = _last_months(as_of)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evidence:
        for theme_id in item.get("theme_ids", []):
            grouped[theme_id].append(item)

    support_totals = {
        definition["id"]: sum(item.get("support_count", 1) for item in grouped.get(definition["id"], []))
        for definition in theme_defs
    }
    effective_totals = {}
    for definition in theme_defs:
        by_source = Counter()
        for item in grouped.get(definition["id"], []):
            by_source[item["source_id"]] += item.get("support_count", 1)
        effective_totals[definition["id"]] = sum(math.log1p(value) for value in by_source.values())
    max_effective_support = max(effective_totals.values(), default=1) or 1
    analyses = []

    for definition in theme_defs:
        theme_id = definition["id"]
        items = grouped.get(theme_id, [])
        source_groups: dict[str, dict[str, int]] = defaultdict(lambda: {"observations": 0, "support_units": 0})
        monthly = Counter({month: 0 for month in months})
        for item in items:
            source = source_groups[item["source_id"]]
            source["observations"] += 1
            source["support_units"] += item.get("support_count", 1)
            for month, count in item.get("monthly_counts", {}).items():
                if month in monthly:
                    monthly[month] += count

        support = support_totals[theme_id]
        source_count = len(source_groups)
        recurrence = round(25 * effective_totals[theme_id] / max_effective_support, 1) if support else 0.0
        prior_rate = sum(monthly[month] for month in months[-4:-2]) / 2
        recent_rate = sum(monthly[month] for month in months[-2:]) / 2
        acceleration = round(max(0, min(25, 12.5 + 10 * math.log2((recent_rate + 1) / (prior_rate + 1)))), 1) if support else 0.0
        persistence = round(25 * sum(monthly[month] > 0 for month in months) / len(months), 1) if support else 0.0
        breadth = round(min(25, source_count * 5), 1)
        total = round(recurrence + acceleration + persistence + breadth, 1)
        dominant = max((row["support_units"] for row in source_groups.values()), default=0)
        concentration = round(dominant / support, 2) if support else None
        if not support:
            maturity = "unobserved"
        elif source_count == 1:
            maturity = "source-specific"
        elif source_count == 2:
            maturity = "emerging"
        elif concentration is not None and concentration >= 0.75:
            maturity = "corroborated-source-concentrated"
        elif source_count >= 4 and total >= 70:
            maturity = "broadly-corroborated"
        else:
            maturity = "corroborated"

        source_breakdown = [
            {"source_id": source_id, **counts}
            for source_id, counts in sorted(source_groups.items(), key=lambda pair: (-pair[1]["support_units"], pair[0]))
        ]
        analyses.append(
            {
                **definition,
                "evidence_count": len(items),
                "support_units": support,
                "source_count": source_count,
                "source_breakdown": source_breakdown,
                "monthly_counts": dict(monthly),
                "source_concentration": concentration,
                "maturity": maturity,
                "score": {
                    "recurrence": recurrence,
                    "acceleration": acceleration,
                    "persistence": persistence,
                    "breadth": breadth,
                    "total": total,
                } if support else None,
                "evidence_ids": [item["id"] for item in items],
            }
        )
    return sorted(analyses, key=lambda item: (-(item.get("score") or {}).get("total", -1), item["name"]))


def _weekly_summary(evidence: list[dict[str, Any]], themes: list[dict[str, Any]], as_of: datetime) -> dict[str, Any]:
    recent_start = as_of - timedelta(days=7)
    prior_start = recent_start - timedelta(days=7)
    recent_counts = Counter()
    prior_counts = Counter()
    recent_records = 0
    for item in evidence:
        if item["evidence_kind"] != "public-source-item":
            continue
        published = _parse_date(item.get("published_at", ""))
        if not published:
            continue
        if recent_start < published <= as_of:
            recent_records += 1
            recent_counts.update(item.get("theme_ids", []))
        elif prior_start < published <= recent_start:
            prior_counts.update(item.get("theme_ids", []))

    name_by_id = {theme["id"]: theme["name"] for theme in themes}
    movements = []
    for theme_id in name_by_id:
        recent, prior = recent_counts[theme_id], prior_counts[theme_id]
        if recent or prior:
            movements.append(
                {
                    "theme_id": theme_id,
                    "name": name_by_id[theme_id],
                    "recent": recent,
                    "prior": prior,
                    "delta": recent - prior,
                    "direction": _movement(recent, prior),
                }
            )
    movements.sort(key=lambda item: (-item["recent"], -item["delta"], item["name"]))
    return {
        "as_of": as_of.date().isoformat(),
        "window_start": recent_start.date().isoformat(),
        "previous_window_start": prior_start.date().isoformat(),
        "new_public_records": recent_records,
        "movements": movements[:10],
        "note": "Weekly movement uses date-level public records only. AlphaSignal aggregate trends remain part of the cross-source theme assessment but are excluded from seven-day deltas.",
    }


def _projects(
    alpha: dict[str, Any],
    public_evidence: list[dict[str, Any]],
    project_evidence_ids: dict[str, str],
    layer_names: dict[str, str],
    project_reviews: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    projects = []
    matched_public_ids: set[str] = set()
    for project in alpha.get("projects", []):
        official = canonical_url(project.get("official_url", ""))
        name = project["name"].casefold()
        matches = []
        for item in public_evidence:
            item_url = canonical_url(item.get("url", ""))
            project_names = " ".join(item.get("projects", [])).casefold()
            title = item.get("title", "").casefold()
            if (official and item_url == official) or name in title or name in project_names:
                matches.append(item)
                matched_public_ids.add(item["id"])
        source_ids = sorted({"alphasignal", *(item["source_id"] for item in matches)})
        projects.append(
            {
                **project,
                "source_ids": source_ids,
                "cross_source": len(source_ids) > 1,
                "evidence_ids": [project_evidence_ids[project["name"]], *(item["id"] for item in matches)],
                "review_status": "reviewed",
            }
        )
    repository_items = [
        item for item in public_evidence
        if item["source_type"] == "repository" and item["id"] not in matched_public_ids
    ]
    for item in repository_items:
        project_name = (item.get("projects") or [item["title"]])[0]
        review = project_reviews.get(project_name)
        project_url = canonical_url(item.get("url", ""))
        related = [
            candidate for candidate in public_evidence
            if candidate["id"] == item["id"]
            or (project_url and canonical_url(candidate.get("url", "")) == project_url)
            or project_name in candidate.get("projects", [])
        ]
        source_ids = sorted({candidate["source_id"] for candidate in related})
        primary_layer_id = item.get("stack_layers", [""])[0] if item.get("stack_layers") else ""
        project_record = {
            "name": project_name,
            "rank": None,
            "editorial_rank": None,
            "source_date": item.get("published_at", ""),
            "category": "Discovered public repository",
            "why_it_matters": item.get("summary") or "Public repository discovered by the configured GitHub queries.",
            "workflow_opportunity": "Not yet assessed. Inspect the repository and linked evidence before deciding whether to test it.",
            "caveat": "Unreviewed discovery; inclusion is not an endorsement and no opportunity score has been assigned.",
            "official_url": item.get("url", ""),
            "primary_layer": layer_names.get(primary_layer_id, "Unclassified"),
            "secondary_layer": None,
            "cross_layer": False,
            "ratings": {},
            "opportunity_score": None,
            "action": "Unreviewed",
            "hype_risk": "N/O",
            "source_ids": source_ids,
            "cross_source": len(source_ids) > 1,
            "evidence_ids": [candidate["id"] for candidate in related],
            "review_status": "reviewed" if review else "unreviewed",
        }
        if review:
            project_record.update(review)
        projects.append(project_record)
    return projects


def _early_signal_directions(
    evidence: list[dict[str, Any]],
    source_defs: dict[str, dict[str, Any]],
    as_of: datetime,
) -> list[dict[str, Any]]:
    """Turn cross-source observations into explicitly bounded directional hypotheses."""
    window_start = as_of - timedelta(days=90)
    directions = []

    for definition in EARLY_SIGNAL_DIRECTIONS:
        theme_ids = definition["theme_ids"]
        # A compound hypothesis needs evidence connecting at least two of its
        # constituent themes; otherwise one broad theme can create false breadth.
        all_items = [
            item for item in evidence
            if len(theme_ids.intersection(item.get("theme_ids", []))) >= 2
        ]
        window_items = [
            item for item in all_items
            if (published := _parse_date(item.get("published_at", ""))) and window_start <= published <= as_of
        ]
        active_items = window_items
        family_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
        family_names: dict[str, str] = {}
        for item in active_items:
            source = source_defs.get(item["source_id"], {})
            channel = source.get("channel", item.get("source_type", "unknown"))
            family_id, family_name = SOURCE_FAMILIES.get(channel, (channel, channel.replace("-", " ").title()))
            family_items[family_id].append(item)
            family_names[family_id] = family_name

        source_ids = sorted({item["source_id"] for item in active_items})
        technical_family_count = len({"builders", "research", "engineering"}.intersection(family_items))
        family_count = len(family_items)
        if not active_items:
            stage = "watch"
            confidence = "unobserved"
        elif technical_family_count == 0 or family_count <= 2:
            stage = "forming"
            confidence = "low"
        elif family_count <= 4 or len(source_ids) < 6:
            stage = "taking-shape"
            confidence = "moderate"
        else:
            stage = "corroborating"
            confidence = "strong"

        family_summary = [
            {
                "id": family_id,
                "name": family_names[family_id],
                "source_ids": sorted({item["source_id"] for item in items}),
                "source_count": len({item["source_id"] for item in items}),
                "evidence_count": len(items),
            }
            for family_id, items in sorted(
                family_items.items(),
                key=lambda pair: (-len({item["source_id"] for item in pair[1]}), pair[0]),
            )
        ]

        # Cite recent evidence while maximizing source-family and publisher diversity.
        candidates = sorted(
            active_items,
            key=lambda item: (item.get("published_at", ""), item["id"]),
            reverse=True,
        )
        selected: list[dict[str, Any]] = []
        selected_families: set[str] = set()
        selected_sources: set[str] = set()
        for item in candidates:
            source = source_defs.get(item["source_id"], {})
            channel = source.get("channel", item.get("source_type", "unknown"))
            family_id = SOURCE_FAMILIES.get(channel, (channel, ""))[0]
            if family_id not in selected_families or item["source_id"] not in selected_sources:
                selected.append(item)
                selected_families.add(family_id)
                selected_sources.add(item["source_id"])
            if len(selected) == 8:
                break
        if len(selected) < 8:
            selected_ids = {item["id"] for item in selected}
            selected.extend(item for item in candidates if item["id"] not in selected_ids)

        dated = [
            (published, item)
            for item in all_items
            if (published := _parse_date(item.get("published_at", "")))
        ]
        directions.append(
            {
                **{key: value for key, value in definition.items() if key != "theme_ids"},
                "theme_ids": sorted(theme_ids),
                "stage": stage,
                "confidence": confidence,
                "window_days": 90,
                "evidence_count": len(active_items),
                "source_ids": source_ids,
                "source_count": len(source_ids),
                "source_families": family_summary,
                "family_count": family_count,
                "technical_family_count": technical_family_count,
                "first_observed": min((published for published, _ in dated), default=None).date().isoformat() if dated else None,
                "last_observed": max((published for published, _ in dated), default=None).date().isoformat() if dated else None,
                "evidence_ids": [item["id"] for item in selected[:8]],
            }
        )

    stage_order = {"forming": 0, "taking-shape": 1, "corroborating": 2, "watch": 3}
    return sorted(
        directions,
        key=lambda item: (stage_order[item["stage"]], -item["family_count"], -item["source_count"], item["title"]),
    )


def build_research(
    public_payload: dict[str, Any],
    alpha: dict[str, Any],
    taxonomy: dict[str, Any],
    mappings: dict[str, Any],
    project_reviews: dict[str, dict[str, Any]] | None = None,
    classification_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = public_payload["meta"]["generated_at"]
    as_of = _parse_date(generated_at) or datetime.now(timezone.utc)
    theme_defs = taxonomy.get("seed_themes", [])
    theme_by_id = {theme["id"]: theme for theme in theme_defs}
    layer_names = {layer["id"]: layer["name"] for layer in taxonomy.get("stack_layers", [])}
    public_evidence = [_normalize_public_evidence(row, theme_by_id) for row in public_payload.get("evidence", [])]
    alpha_evidence, project_ids = _normalize_alpha_evidence(alpha, theme_by_id, mappings)
    evidence = sorted(public_evidence + alpha_evidence, key=lambda item: (item.get("published_at", ""), item["id"]), reverse=True)
    themes = _theme_analyses(evidence, theme_defs, as_of)
    projects = _projects(alpha, public_evidence, project_ids, layer_names, project_reviews or {})
    evidence_by_id = {item["id"]: item for item in evidence}
    for project in projects:
        linked = [evidence_by_id[evidence_id] for evidence_id in project["evidence_ids"] if evidence_id in evidence_by_id]
        project["theme_ids"] = sorted({theme_id for item in linked for theme_id in item.get("theme_ids", [])})
        if project["review_status"] == "reviewed":
            project["review_priority"] = project.get("opportunity_score")
            project["review_reason"] = (
                f"{project.get('verification_level')} completed {project.get('reviewed_at')}."
                if project.get("verification_level") and project.get("reviewed_at")
                else "Reviewed assessment with an explicit opportunity score."
            )
            continue
        published = _parse_date(project.get("source_date", ""))
        age_days = (as_of - published).days if published else 9999
        priority = 20 * len(project["theme_ids"]) + (25 if project["cross_source"] else 0)
        priority += 20 if age_days <= 30 else 10 if age_days <= 90 else 0
        project["review_priority"] = min(100, priority)
        project["review_reason"] = (
            f"{len(project['theme_ids'])} matched concepts; "
            f"{len(project['source_ids'])} evidence source{'s' if len(project['source_ids']) != 1 else ''}; "
            f"last observed {project.get('source_date') or 'N/O'}."
        )

    def project_recency(project: dict[str, Any]) -> float:
        published = _parse_date(project.get("source_date", ""))
        return published.timestamp() if published else 0

    ranked_candidates = sorted(
        (project for project in projects if project["review_status"] != "reviewed" and project["theme_ids"]),
        key=lambda project: (-project["review_priority"], -project_recency(project), project["name"]),
    )
    queue_candidates: list[dict[str, Any]] = []
    signature_counts: Counter[tuple[str, ...]] = Counter()
    for project in ranked_candidates:
        signature = tuple(project["theme_ids"])
        if signature_counts[signature] >= 3:
            continue
        queue_candidates.append(project)
        signature_counts[signature] += 1
        if len(queue_candidates) == 25:
            break
    if len(queue_candidates) < 25:
        queued_candidate_names = {project["name"] for project in queue_candidates}
        queue_candidates.extend(
            project for project in ranked_candidates
            if project["name"] not in queued_candidate_names
        )
        queue_candidates = queue_candidates[:25]
    queued_names = {project["name"] for project in queue_candidates}
    for project in projects:
        if project["review_status"] == "reviewed":
            continue
        if project["name"] in queued_names:
            project["review_status"] = "queued"
            project["action"] = "Review next"
        else:
            project["review_status"] = "discovered"
            project["action"] = "Discovered"
    reviewed_projects = sorted(
        (project for project in projects if project["review_status"] == "reviewed"),
        key=lambda project: (-(project.get("opportunity_score") or 0), project["name"]),
    )
    for rank, project in enumerate(reviewed_projects, start=1):
        project["rank"] = rank
    non_reviewed_projects = sorted(
        (project for project in projects if project["review_status"] != "reviewed"),
        key=lambda project: (
            0 if project["review_status"] == "queued" else 1,
            -(project.get("review_priority") or 0),
            -project_recency(project),
            project["name"],
        ),
    )
    projects = reviewed_projects + non_reviewed_projects
    queued_projects = [project for project in projects if project["review_status"] == "queued"]
    discovered_projects = [project for project in projects if project["review_status"] == "discovered"]

    source_defs = {source["id"]: dict(source) for source in public_payload.get("sources", [])}
    source_defs.setdefault(
        "alphasignal",
        {
            "id": "alphasignal",
            "name": "AlphaSignal",
            "channel": "newsletter",
            "source_quality": "medium",
            "commercial_bias": "disclosed-and-mixed",
        },
    )
    counts = Counter(item["source_id"] for item in evidence)
    dates_by_source: dict[str, list[datetime]] = defaultdict(list)
    for item in evidence:
        if published := _parse_date(item.get("published_at", "")):
            dates_by_source[item["source_id"]].append(published)
    sources = []
    for source_id, source in source_defs.items():
        source["normalized_evidence_count"] = counts[source_id]
        source["status"] = "active" if counts[source_id] else "configured"
        latest = max(dates_by_source[source_id], default=None)
        source["last_observed_at"] = latest.isoformat() if latest else None
        if not latest:
            source["freshness"] = "configured"
        else:
            age_days = max(0, (as_of - latest).days)
            source["freshness"] = "recent" if age_days <= 30 else "aging" if age_days <= 90 else "historical"
        sources.append(source)
    sources.sort(key=lambda source: (-source["normalized_evidence_count"], source["name"]))
    active_source_ids = [source["id"] for source in sources if source["status"] == "active"]
    expert_social_items = [item for item in public_evidence if item["source_type"] == "expert-social"]
    classified_expert_items = [item for item in expert_social_items if item.get("theme_ids")]
    expert_source_ids = sorted({item["source_id"] for item in expert_social_items})
    expert_theme_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in classified_expert_items:
        for theme_id in item["theme_ids"]:
            expert_theme_items[theme_id].append(item)
    expert_theme_summary = sorted(
        (
            {
                "theme_id": theme_id,
                "evidence_count": len(items),
                "source_ids": sorted({item["source_id"] for item in items}),
                "source_count": len({item["source_id"] for item in items}),
                "evidence_ids": [
                    item["id"]
                    for item in sorted(items, key=lambda row: (row.get("published_at", ""), row["id"]), reverse=True)
                ],
            }
            for theme_id, items in expert_theme_items.items()
        ),
        key=lambda row: (-row["source_count"], -row["evidence_count"], row["theme_id"]),
    )

    def expert_subset(theme_ids: set[str]) -> list[dict[str, Any]]:
        return [item for item in classified_expert_items if theme_ids.intersection(item["theme_ids"])]

    def expert_evidence_ids(theme_ids: set[str], limit: int = 5) -> list[str]:
        candidates = sorted(
            expert_subset(theme_ids),
            key=lambda item: (item.get("published_at", ""), item["id"]),
            reverse=True,
        )
        selected: list[dict[str, Any]] = []
        seen_sources: set[str] = set()
        for item in candidates:
            if item["source_id"] not in seen_sources:
                selected.append(item)
                seen_sources.add(item["source_id"])
            if len(selected) == limit:
                break
        if len(selected) < limit:
            selected_ids = {item["id"] for item in selected}
            selected.extend(item for item in candidates if item["id"] not in selected_ids)
        return [item["id"] for item in selected[:limit]]

    def expert_stats(theme_ids: set[str]) -> tuple[int, int]:
        items = expert_subset(theme_ids)
        return len(items), len({item["source_id"] for item in items})

    def expert_strength(expert_count: int) -> tuple[str, str]:
        if expert_count >= 3:
            return "strong", "Cross-expert pattern"
        if expert_count == 2:
            return "emerging", "Emerging agreement"
        return "watch", "Source-specific watch"

    evaluation_themes = {"training-self-improvement"}
    agent_operations_themes = {"agent-harnesses", "coding-agents", "assurance-infrastructure"}
    model_fit_themes = {"small-specialized-models", "open-local-inference", "model-routing"}
    evaluation_count, evaluation_experts = expert_stats(evaluation_themes)
    agent_count, agent_experts = expert_stats(agent_operations_themes)
    model_fit_count, model_fit_experts = expert_stats(model_fit_themes)
    evaluation_strength, evaluation_label = expert_strength(evaluation_experts)
    agent_strength, agent_label = expert_strength(agent_experts)
    model_fit_strength, model_fit_label = expert_strength(model_fit_experts)
    expert_findings = [
        {
            "id": "evaluation-as-system-design",
            "strength": evaluation_strength,
            "label": evaluation_label,
            "title": "Evaluation is moving from a final benchmark into the system-design loop",
            "analysis": f"{evaluation_count} classified posts across {evaluation_experts} experts discuss evaluation, training feedback, or self-improvement. The shared engineering direction is toward measuring behavior continuously while the system is being built, rather than treating one benchmark score as a release verdict.",
            "why_it_matters": "Agent quality depends on task-specific traces, failure categories, and feedback loops that reveal whether a change improves the complete system—not only the base model.",
            "workflow_opportunity": "Capture representative workflow traces, label failure modes, and run the same evaluation set whenever prompts, models, tools, or harness logic change.",
            "caveat": "The posts identify an engineering priority; they do not establish one accepted evaluation method or prove that self-improving systems are reliable.",
            "theme_ids": sorted(evaluation_themes),
            "evidence_ids": expert_evidence_ids(evaluation_themes),
            "metrics": {"posts": evaluation_count, "experts": evaluation_experts},
        },
        {
            "id": "agent-operating-layer",
            "strength": agent_strength,
            "label": agent_label,
            "title": "Attention is shifting from agent demos to the operating layer around them",
            "analysis": f"{agent_count} posts across {agent_experts} experts connect harness behavior, coding agents, or assurance. The common concern is not simply whether a model can act, but how its context, tools, permissions, and failure recovery are engineered.",
            "why_it_matters": "The durable engineering surface may be the execution and control environment that makes many models dependable, inspectable, and replaceable.",
            "workflow_opportunity": "Treat the harness as a product: log every decision, isolate execution, validate outputs, and preserve a human-readable recovery path for failed runs.",
            "caveat": "This grouping joins adjacent observations from different experts. It is a directional synthesis, not evidence that they endorse an identical architecture.",
            "theme_ids": sorted(agent_operations_themes),
            "evidence_ids": expert_evidence_ids(agent_operations_themes),
            "metrics": {"posts": agent_count, "experts": agent_experts},
        },
        {
            "id": "task-shaped-models",
            "strength": model_fit_strength,
            "label": model_fit_label,
            "title": "Task-shaped models are becoming an engineering alternative to universal-model calls",
            "analysis": f"{model_fit_count} posts across {model_fit_experts} experts point toward small, open, local, or routed models selected for a specific decision. The emerging idea is to spend frontier-model reasoning only where the workflow actually requires it.",
            "why_it_matters": "Separating routine decisions from open-ended reasoning can reduce latency and cost while making outputs easier to constrain and evaluate.",
            "workflow_opportunity": "Profile an expensive agent loop, isolate repeated classification or routing decisions, and compare a specialized model against the frontier-model baseline on quality, latency, and cost.",
            "caveat": "Current expert-social support is limited. Product announcements and repository activity elsewhere in the radar provide context, not additional expert agreement.",
            "theme_ids": sorted(model_fit_themes),
            "evidence_ids": expert_evidence_ids(model_fit_themes),
            "metrics": {"posts": model_fit_count, "experts": model_fit_experts},
        },
    ]
    expert_findings = [finding for finding in expert_findings if finding["metrics"]["posts"]]
    narrative_source_ids = sorted(
        source["id"]
        for source in sources
        if source["status"] == "active" and source.get("channel") in {"operator-essay", "investor-essay"}
    )
    non_narrative_prefixes = ("welcome", "congratulations", "meet ", "adding ", "demo day")
    narrative_items = [
        item for item in public_evidence
        if item["source_id"] in narrative_source_ids
        and not item.get("title", "").casefold().startswith(non_narrative_prefixes)
    ]
    classified_narrative_items = [item for item in narrative_items if item.get("theme_ids")]
    classified_narrative_source_ids = sorted({item["source_id"] for item in classified_narrative_items})
    narrative_status = "complete" if len(narrative_source_ids) >= 5 and len(classified_narrative_source_ids) >= 5 else "active"
    narrative_source_names = [source_defs[source_id]["name"] for source_id in narrative_source_ids]
    narrative_theme_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in classified_narrative_items:
        for theme_id in item["theme_ids"]:
            narrative_theme_items[theme_id].append(item)
    narrative_theme_summary = sorted(
        (
            {
                "theme_id": theme_id,
                "evidence_count": len(items),
                "source_ids": sorted({item["source_id"] for item in items}),
                "source_count": len({item["source_id"] for item in items}),
            }
            for theme_id, items in narrative_theme_items.items()
        ),
        key=lambda row: (-row["source_count"], -row["evidence_count"], row["theme_id"]),
    )
    theme_analysis_by_id = {theme["id"]: theme for theme in themes}

    def narrative_subset(theme_ids: set[str]) -> list[dict[str, Any]]:
        return [item for item in classified_narrative_items if theme_ids.intersection(item["theme_ids"])]

    def narrative_evidence_ids(theme_ids: set[str], limit: int = 4) -> list[str]:
        candidates = sorted(
            narrative_subset(theme_ids),
            key=lambda item: (item.get("published_at", ""), item["id"]),
            reverse=True,
        )
        selected: list[dict[str, Any]] = []
        seen_sources: set[str] = set()
        for item in candidates:
            if item["source_id"] not in seen_sources:
                selected.append(item)
                seen_sources.add(item["source_id"])
            if len(selected) == limit:
                break
        if len(selected) < limit:
            selected_ids = {item["id"] for item in selected}
            selected.extend(item for item in candidates if item["id"] not in selected_ids)
        return [item["id"] for item in selected[:limit]]

    def narrative_stats(theme_ids: set[str]) -> tuple[int, int]:
        items = narrative_subset(theme_ids)
        return len(items), len({item["source_id"] for item in items})

    outcome_themes = {"enterprise-vertical-ai", "agent-harnesses", "ai-native-gtm"}
    assurance_themes = {"assurance-infrastructure"}
    coding_themes = {"coding-agents"}
    inference_themes = {"frontier-inference-infrastructure", "model-routing"}
    physical_themes = {"robotics-embodied-ai", "multimodal-3d"}
    gtm_themes = {"ai-native-gtm"}
    outcome_count, outcome_sources = narrative_stats(outcome_themes)
    assurance_count, assurance_sources = narrative_stats(assurance_themes)
    coding_count, coding_sources = narrative_stats(coding_themes)
    inference_count, inference_sources = narrative_stats(inference_themes)
    physical_count, physical_sources = narrative_stats(physical_themes)
    gtm_count, gtm_sources = narrative_stats(gtm_themes)
    assurance_global = theme_analysis_by_id["assurance-infrastructure"]
    coding_global = theme_analysis_by_id["coding-agents"]

    narrative_findings = [
        {
            "id": "workflow-ownership",
            "strength": "moderate",
            "label": "Cross-source pattern",
            "title": "The commercial narrative has moved from copilots to workflow ownership",
            "analysis": f"{outcome_count} essays across {outcome_sources} publishers describe AI as a workforce, teammate, revenue engine, system of action, autopilot, or employee. The shared product thesis is not a better interface for a human task; it is a bounded system that carries the task from trigger to outcome.",
            "why_it_matters": "If this framing holds, products will be judged on completed work, exception handling, and measurable operating outcomes—not primarily on model quality or chat experience.",
            "workflow_opportunity": "Choose one workflow with a clear trigger, handoffs, and completion state. Let an agent execute the routine path, route exceptions to a human, and measure cycle time, intervention rate, and error cost.",
            "caveat": "The evidence comes from two investors writing about portfolio companies. It is a coherent thesis, not proof of broad customer adoption.",
            "theme_ids": sorted(outcome_themes),
            "evidence_ids": narrative_evidence_ids(outcome_themes),
            "metrics": {"essays": outcome_count, "publishers": outcome_sources},
        },
        {
            "id": "assurance-layer",
            "strength": "strong",
            "label": "Strongest narrative consensus",
            "title": "Assurance is becoming a separate infrastructure layer for agents",
            "analysis": f"{assurance_count} essays across {assurance_sources} publishers converge on runtime controls: vulnerability discovery, penetration testing, identity, data sovereignty, defensive models, and detection of abnormal agent intent. In the wider radar this theme appears across {assurance_global['source_count']} sources and {assurance_global['support_units']} support units.",
            "why_it_matters": "As agents gain permission to act, the deployment bottleneck moves from raw capability to whether their behavior can be observed, constrained, investigated, and trusted.",
            "workflow_opportunity": "Build a reusable assurance wrapper around agent workflows: complete action logs, policy gates, sandbox boundaries, anomaly detection, evaluation suites, and human escalation for high-impact steps.",
            "caveat": "Most narrative evidence is cybersecurity-focused. General agent governance is a reasoned extension, not yet equally demonstrated across every workflow category.",
            "theme_ids": sorted(assurance_themes),
            "evidence_ids": narrative_evidence_ids(assurance_themes),
            "metrics": {"essays": assurance_count, "publishers": assurance_sources},
        },
        {
            "id": "coding-agent-stack",
            "strength": "strong",
            "label": "Corroborated infrastructure thesis",
            "title": "The coding-agent opportunity is shifting below the assistant interface",
            "analysis": f"{coding_count} essays across {coding_sources} publishers focus on the environment around the agent: a full-stack cloud, software implementation, production operations, and scientific judgment. The broader coding-agent theme scores {coding_global['score']['total']} and appears across {coding_global['source_count']} radar sources.",
            "why_it_matters": "The durable layer may be the context, execution environment, verification, and operational control that lets agents finish real work—not another chat surface around a frontier model.",
            "workflow_opportunity": "Prototype a repository task runner that provisions an isolated environment, assembles relevant context, executes the agent, tests the result, and presents a reviewable change with traces and rollback.",
            "caveat": "The evidence mixes coding, implementation, research, and operations. Their shared infrastructure needs are clearer than a single winning product category.",
            "theme_ids": sorted(coding_themes),
            "evidence_ids": narrative_evidence_ids(coding_themes),
            "metrics": {"essays": coding_count, "publishers": coding_sources},
        },
        {
            "id": "inference-control-plane",
            "strength": "emerging",
            "label": "Emerging thesis",
            "title": "Inference is being productized as a control plane, not a commodity endpoint",
            "analysis": f"{inference_count} essays across {inference_sources} publishers frame specialized runtimes, inference clusters, and model routing as products in their own right. The common bet is that cost, latency, model selection, and workload fit will require active control rather than a single default provider.",
            "why_it_matters": "A heterogeneous model market creates value above raw compute: routing, benchmarking, caching, capacity selection, and policy-aware fallback can materially change unit economics and reliability.",
            "workflow_opportunity": "Instrument one expensive AI workflow across several models and runtimes. Route by task type and service objective, then compare quality, latency, failure rate, and cost per accepted outcome.",
            "caveat": "This is a small, recent sample. Treat it as a monitored infrastructure thesis, not an established market structure.",
            "theme_ids": sorted(inference_themes),
            "evidence_ids": narrative_evidence_ids(inference_themes),
            "metrics": {"essays": inference_count, "publishers": inference_sources},
        },
        {
            "id": "physical-ai-simulation",
            "strength": "emerging",
            "label": "Emerging cross-source pattern",
            "title": "Physical AI is being organized around world models and simulation before deployment",
            "analysis": f"{physical_count} essays across {physical_sources} publishers connect spatial world models, robotics, and high-fidelity simulation. The recurring idea is that embodied systems need safe, scalable environments in which to learn, test, and validate before acting in the physical world.",
            "why_it_matters": "For robotics and physical systems, synthetic experience and validation infrastructure may be a nearer-term enabling layer than a general-purpose robot application.",
            "workflow_opportunity": "Build domain-specific simulation and evaluation loops that generate edge cases, replay failures, and gate physical deployment against measurable safety and task-performance thresholds.",
            "caveat": "The signal comes from two publishers and four essays. Commercial timing, transfer from simulation, and deployment economics remain unresolved.",
            "theme_ids": sorted(physical_themes),
            "evidence_ids": narrative_evidence_ids(physical_themes),
            "metrics": {"essays": physical_count, "publishers": physical_sources},
        },
        {
            "id": "ai-native-gtm-watch",
            "strength": "watch",
            "label": "Source-specific watch",
            "title": "AI-native GTM is a named category, but not yet a cross-source conclusion",
            "analysis": f"{gtm_count} essays from {gtm_sources} publisher describe an AI revenue engine and a system of action for organic growth. The interesting abstraction is a closed loop from market signal to executed action, but independent narrative confirmation is absent in this corpus.",
            "why_it_matters": "The useful distinction is between generating sales or marketing content and continuously sensing, deciding, and acting across a revenue workflow.",
            "workflow_opportunity": "Test one closed-loop motion—such as inbound qualification or organic-content refresh—with explicit triggers, approvals, CRM writes, attribution, and a measurable revenue or pipeline outcome.",
            "caveat": "Both observations come from Greylock. Keep this on the watchlist until another publisher or technical source independently supports the category.",
            "theme_ids": sorted(gtm_themes),
            "evidence_ids": narrative_evidence_ids(gtm_themes),
            "metrics": {"essays": gtm_count, "publishers": gtm_sources},
        },
    ]

    early_directions = _early_signal_directions(evidence, source_defs, as_of)
    early_evidence_ids = sorted({evidence_id for direction in early_directions for evidence_id in direction["evidence_ids"]})
    early_source_ids = sorted({source_id for direction in early_directions for source_id in direction["source_ids"]})

    engineering_concepts = []
    for theme in themes:
        concept_projects = [project for project in projects if theme["id"] in project.get("theme_ids", [])]
        if not concept_projects:
            continue
        concept_projects.sort(
            key=lambda project: (
                0 if project["review_status"] == "reviewed" else 1 if project["review_status"] == "queued" else 2,
                -(project.get("opportunity_score") or project.get("review_priority") or 0),
                project["name"],
            )
        )
        engineering_concepts.append(
            {
                "id": theme["id"],
                "name": theme["name"],
                "definition": theme["definition"],
                "primary_layer": theme.get("primary_layer"),
                "secondary_layer": theme.get("secondary_layer"),
                "maturity": theme["maturity"],
                "source_count": theme["source_count"],
                "evidence_count": theme["evidence_count"],
                "project_count": len(concept_projects),
                "reviewed_project_count": sum(project["review_status"] == "reviewed" for project in concept_projects),
                "queued_project_count": sum(project["review_status"] == "queued" for project in concept_projects),
                "project_names": [project["name"] for project in concept_projects[:8]],
            }
        )
    engineering_concepts.sort(
        key=lambda concept: (
            -concept["reviewed_project_count"],
            -concept["queued_project_count"],
            -concept["project_count"],
            concept["name"],
        )
    )
    classified_public_count = sum(bool(item.get("theme_ids")) for item in public_evidence)
    classification_coverage = round(classified_public_count / len(public_evidence), 3) if public_evidence else None
    recent_source_count = sum(source.get("freshness") == "recent" for source in sources)
    aging_source_count = sum(source.get("freshness") == "aging" for source in sources)
    historical_source_count = sum(source.get("freshness") == "historical" for source in sources)
    published_classification_audit = None
    if classification_audit:
        published_classification_audit = {
            **classification_audit,
            "current_unclassified_records": len(public_evidence) - classified_public_count,
            "current_classification_coverage": classification_coverage,
        }
    engineering_atlas = {
        "title": "Engineering Atlas",
        "summary": "A connected registry of engineering concepts, reviewed tools, and public repository discoveries. Discovery is not endorsement; judgment appears only after review.",
        "concepts": engineering_concepts,
        "quality": {
            "classification_coverage": classification_coverage,
            "classified_public_records": classified_public_count,
            "unclassified_public_records": len(public_evidence) - classified_public_count,
            "classification_review_records": len(public_evidence) - classified_public_count,
            "recent_sources": recent_source_count,
            "aging_sources": aging_source_count,
            "historical_sources": historical_source_count,
            "reviewed_projects": len(reviewed_projects),
            "queued_projects": len(queued_projects),
            "discovered_projects": len(discovered_projects),
        },
        "classification_audit": published_classification_audit,
        "freshness_note": "Freshness is based on the latest dated evidence observed for each source, not a direct collector-uptime check. Recent means 30 days or less; aging means 31–90 days; historical means more than 90 days.",
    }

    analyses = [
        {
            "id": "cross-source-landscape",
            "title": "Cross-source AI landscape",
            "question": "Which themes are repeated across independent source channels, and where is attention changing?",
            "summary": "Combined theme assessments across first-party lab publications, newsletter analysis, papers, repositories, essays, and technical discussion.",
            "status": "active",
            "source_ids": active_source_ids,
            "evidence_count": len(evidence),
            "updated_at": generated_at,
        },
        {
            "id": "alphasignal-corpus",
            "title": "AlphaSignal corpus",
            "question": "What capabilities, projects, and stack shifts recurred across the private newsletter archive?",
            "summary": (
                f"Reviewed analysis of {alpha['meta']['email_count']} emails and "
                f"{alpha['meta']['unique_catalog_records']} unique catalog records; "
                "published as aggregates and project assessments."
            ),
            "status": "complete",
            "source_ids": ["alphasignal"],
            "evidence_count": len(alpha_evidence),
            "underlying_records": alpha["meta"]["unique_catalog_records"],
            "updated_at": alpha["meta"]["analysis_date"],
        },
        {
            "id": "public-signal-monitor",
            "title": "Public signal monitor",
            "question": "What is appearing across first-party labs, expert newsletters, practitioner writing, papers, repositories, essays, and technical discussion?",
            "summary": "Continuously collected public metadata, first-party claims, expert interpretation, and curated roundups classified with the same taxonomy as the newsletter research.",
            "status": public_payload["meta"]["status"],
            "source_ids": sorted({item["source_id"] for item in public_evidence}),
            "evidence_count": len(public_evidence),
            "updated_at": generated_at,
        },
        {
            "id": "early-signal-tracker",
            "title": "Early Signal Tracker",
            "question": "Where does the combined evidence suggest the AI industry is heading before the direction becomes an established signal?",
            "summary": "Directional hypotheses connect weak signals across experts, engineering artifacts, research, first-party builders, and operator or investor narratives without presenting attention as adoption.",
            "status": "active" if early_evidence_ids else "configured",
            "source_ids": early_source_ids,
            "evidence_count": len(early_evidence_ids),
            "direction_count": len(early_directions),
            "directions": early_directions,
            "executive_summary": "The current corpus points toward a more modular and operational AI industry: agents own bounded workflows; models are selected inside heterogeneous inference systems; governed context connects agents to live business state; and assurance becomes part of the release path. Physical AI is earlier, with simulation and validation emerging as the enabling layer. These are hypotheses to monitor, not forecasts of adoption.",
            "interpretation_note": "A direction's stage is based on evidence that connects at least two constituent themes and on independent source-family breadth inside a rolling 90-day window. It measures whether a compound hypothesis is appearing in different kinds of evidence—not market size, technical correctness, or inevitability. Supporting links are selected for source diversity rather than popularity.",
            "updated_at": generated_at,
        },
        {
            "id": "expert-pulse",
            "title": "Expert pulse",
            "question": "Which technical ideas, tools, and capability claims are appearing across curated AI experts on Bluesky?",
            "summary": (
                f"{len(classified_expert_items)} relevant public posts from {len(expert_source_ids)} curated experts, "
                "classified with the same taxonomy as the rest of the radar."
            ),
            "status": "active" if expert_social_items else "configured",
            "source_ids": expert_source_ids,
            "evidence_count": len(classified_expert_items),
            "corpus_count": len(expert_social_items),
            "evidence_ids": [item["id"] for item in classified_expert_items],
            "executive_summary": "The strongest shared expert signal is methodological: evaluation and feedback are becoming part of system design. A second cluster concerns the operating layer around agents—context, tools, permissions, execution, and recovery. Specialized and routed models are a plausible efficiency direction, but expert-social corroboration remains limited.",
            "findings": expert_findings,
            "theme_summary": expert_theme_summary,
            "interpretation_note": "Bluesky posts are expert observations and discovery leads. They can identify an emerging idea or artifact, but they do not independently verify a technical claim. Reposts, replies, engagement counts, and off-topic posts are excluded.",
            "updated_at": generated_at,
        },
        {
            "id": "operator-narratives",
            "title": "Operator and investor narratives",
            "question": "Which categories are being named or framed by startup operators and investors before broad technical corroboration?",
            "summary": f"Official writing from {', '.join(narrative_source_names)} analyzed against the shared taxonomy and compared with the wider evidence base.",
            "status": narrative_status,
            "source_ids": narrative_source_ids,
            "evidence_count": len(classified_narrative_items),
            "corpus_count": len(narrative_items),
            "classified_source_count": len(classified_narrative_source_ids),
            "evidence_ids": [item["id"] for item in classified_narrative_items],
            "executive_summary": "The corpus does not point to one winning application category. It points to a product architecture: agents own bounded workflows; specialized runtime, context, and infrastructure make them usable; assurance controls make them deployable. Independent agreement is strongest around assurance and coding-agent infrastructure. Inference, physical AI, and AI-native GTM are earlier signals, not established conclusions.",
            "interpretation_note": "These are narrative signals from investor and operator writing, not market-size or adoption estimates. Counts refer to classified essays and distinct publishers; commercial bias is retained in the source metadata.",
            "findings": narrative_findings,
            "theme_summary": narrative_theme_summary,
            "coverage_target": 5,
            "updated_at": generated_at,
        },
        {
            "id": "project-opportunities",
            "title": "Project opportunity assessment",
            "question": "Which concrete projects appear worth testing for workflow automation?",
            "summary": "Twenty reviewed projects with separate opportunity scores, hype risk, provenance, and public corroboration where available.",
            "status": "complete",
            "source_ids": sorted({source_id for project in reviewed_projects for source_id in project["source_ids"]}),
            "evidence_count": len(reviewed_projects),
            "updated_at": alpha["meta"]["analysis_date"],
        },
    ]

    return {
        "meta": {
            "title": "AI Signal Radar cross-source research",
            "generated_at": generated_at,
            "status": "success" if evidence else "empty",
            "normalized_evidence_count": len(evidence),
            "public_record_count": len(public_evidence),
            "active_source_count": len(active_source_ids),
            "theme_count": len(themes),
            "observed_theme_count": sum(theme["evidence_count"] > 0 for theme in themes),
            "project_count": len(projects),
            "reviewed_project_count": len(reviewed_projects),
            "queued_project_count": len(queued_projects),
            "discovered_project_count": len(discovered_projects),
            "classification_coverage": classification_coverage,
            "recent_source_count": recent_source_count,
            "model": "Every source is normalized into the same evidence contract. Source-specific analyses remain inspectable but do not define the global navigation.",
        },
        "analyses": analyses,
        "weekly": _weekly_summary(evidence, themes, as_of),
        "themes": themes,
        "projects": projects,
        "engineering_atlas": engineering_atlas,
        "evidence": evidence,
        "sources": sources,
        "methodology": {
            "normalization": "Public source items and sanitized AlphaSignal aggregates share one evidence contract with source, date, themes, stack layers, support counts, and provenance.",
            "trend_score": {
                "recurrence": "Relative log-scaled support units across all themes, 25 points.",
                "acceleration": "Most recent two months compared with the preceding two months, 25 points.",
                "persistence": "Active months in the six-month analysis window, 25 points.",
                "breadth": "Five points per contributing source, capped at 25.",
            },
            "limits": [
                "Support units measure source attention, not market adoption or technical quality.",
                "AlphaSignal contributes aggregate mention counts; public sources contribute individual records.",
                "Source concentration is shown because a high score can still be dominated by one source.",
                "First-party lab publications establish what an organization announced or claimed; they do not independently validate performance or adoption.",
                "Expert newsletters and practitioner blogs contribute interpretation. Curated roundups can repeat announcements already present elsewhere: they add attention breadth, but do not independently validate technical claims.",
                "Curated Bluesky posts are treated as expert observations. Engagement is ignored, and the same publisher is counted once across its social, blog, and newsletter channels.",
                "Hugging Face may curate papers also present on arXiv; the source breakdown makes this visible.",
                "Keyword classification is deterministic and inspectable but can miss unusual language or create false positives.",
                "Seven-day movement excludes month-level AlphaSignal aggregates because their dates are not equally precise.",
            ],
        },
    }


def weekly_markdown(payload: dict[str, Any]) -> str:
    weekly = payload["weekly"]
    lines = [
        f"# Cross-source AI signal brief — {weekly['as_of']}",
        "",
        f"{payload['meta']['normalized_evidence_count']} normalized evidence records across {payload['meta']['active_source_count']} active sources.",
        f"{payload['meta']['observed_theme_count']} of {payload['meta']['theme_count']} tracked themes are observed.",
        "",
        "## Seven-day movement",
        "",
        "| Theme | Current | Previous | Change | Direction |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for movement in weekly["movements"]:
        delta = f"{movement['delta']:+d}"
        lines.append(f"| {movement['name']} | {movement['recent']} | {movement['prior']} | {delta} | {movement['direction']} |")
    if not weekly["movements"]:
        lines.append("| No classified activity | 0 | 0 | 0 | inactive |")
    lines.extend(["", f"> {weekly['note']}", "", "## Strongest cross-source themes", ""])
    for theme in payload["themes"][:10]:
        score = theme["score"]["total"] if theme["score"] else "N/O"
        lines.append(f"- **{theme['name']}** — score {score}; {theme['source_count']} sources; {theme['support_units']} support units; {theme['maturity']}.")
    lines.extend(["", "## Method boundary", "", "Scores measure attention and corroboration in the collected corpus, not market adoption. Source-specific support and concentration remain inspectable in the public dataset.", ""])
    return "\n".join(lines)


def write_weekly_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(weekly_markdown(payload), encoding="utf-8")
