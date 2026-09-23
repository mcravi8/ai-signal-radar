from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TECHNICAL_SOURCE_TYPES = {"paper", "repository", "first-party-lab", "practitioner-blog"}
MATURITY_ORDER = ["narrative", "experimental", "emerging", "established", "baseline"]


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _linked_requirement(target: str, requirements: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in requirements if item.get("source_analysis") == target), None)


def _candidate_metrics(
    evidence_ids: list[str],
    evidence_by_id: dict[str, dict[str, Any]],
    as_of: datetime,
) -> dict[str, Any]:
    records = [evidence_by_id[item_id] for item_id in evidence_ids if item_id in evidence_by_id]
    source_ids = {item.get("source_id") for item in records if item.get("source_id")}
    source_types = {item.get("source_type") for item in records if item.get("source_type")}
    recent_start = as_of - timedelta(days=7)
    recent_count = sum(
        bool(published and recent_start < published <= as_of)
        for item in records
        if (published := _parse_date(item.get("published_at")))
    )
    technical_records = sum(item.get("source_type") in TECHNICAL_SOURCE_TYPES for item in records)
    return {
        "evidence_count": len(records),
        "source_count": len(source_ids),
        "source_types": sorted(source_types),
        "recent_evidence_count": recent_count,
        "technical_record_count": technical_records,
    }


def _movement_points(movement: str) -> int:
    return {
        "new": 25,
        "accelerating": 22,
        "rising": 22,
        "resurfacing": 18,
        "steady": 8,
        "cooling": 3,
        "falling": 3,
        "fading": 0,
        "inactive": 0,
    }.get(movement, 8)


def _priority(candidate: dict[str, Any], linked: bool) -> dict[str, int]:
    source_count = candidate["metrics"]["source_count"]
    family_count = candidate["metrics"].get("family_count", len(candidate["metrics"]["source_types"]))
    technical = candidate["metrics"]["technical_record_count"]
    recent = candidate["metrics"]["recent_evidence_count"]
    components = {
        "momentum": _movement_points(candidate.get("movement", "steady")),
        "source_breadth": min(25, source_count * 3 + family_count * 2),
        "technical_support": min(20, technical * 3),
        "new_evidence": min(20, recent * 4),
        "operating_relevance": 10 if linked else 0,
    }
    components["total"] = sum(components.values())
    return components


def _material_changes(
    candidate: dict[str, Any],
    previous: dict[str, Any] | None,
    thresholds: dict[str, int],
) -> list[str]:
    if previous is None:
        return ["New to the weekly candidate baseline"]
    reasons = []
    for field, label in (("stage", "Lifecycle stage"), ("movement", "Movement"), ("strength", "Finding strength")):
        before, after = previous.get(field), candidate.get(field)
        if before and after and before != after:
            reasons.append(f"{label} changed from {before} to {after}")
    current_metrics = candidate["metrics"]
    previous_metrics = previous.get("metrics", {})
    evidence_delta = current_metrics["evidence_count"] - previous_metrics.get("evidence_count", 0)
    source_delta = current_metrics["source_count"] - previous_metrics.get("source_count", 0)
    if evidence_delta >= thresholds["evidence_count_delta"]:
        reasons.append(f"Evidence increased by {evidence_delta}")
    if source_delta >= thresholds["source_count_delta"]:
        reasons.append(f"Source breadth increased by {source_delta}")
    recent_delta = current_metrics["recent_evidence_count"] - previous_metrics.get("recent_evidence_count", 0)
    if recent_delta > 0:
        reasons.append(f"{recent_delta} additional dated records entered the latest seven-day window")
    previous_score = previous.get("priority", {}).get("total", 0)
    current_score = candidate.get("priority", {}).get("total", 0)
    if abs(current_score - previous_score) >= thresholds["priority_score_delta"]:
        reasons.append(f"Review priority changed by {current_score - previous_score:+d}")
    return reasons


def _candidate_pool(
    research: dict[str, Any],
    operating_model: dict[str, Any],
    previous_review: dict[str, Any] | None,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    analyses = {item["id"]: item for item in research.get("analyses", [])}
    evidence_by_id = {item["id"]: item for item in research.get("evidence", [])}
    requirements = operating_model.get("requirements", [])
    requirements_by_id = {item["id"]: item for item in requirements}
    adjudications = {
        item["candidate_id"]: item
        for item in config.get("candidate_adjudications", [])
    }
    as_of = _parse_date(research.get("meta", {}).get("generated_at")) or datetime.now(timezone.utc)
    previous_by_id = {
        item["id"]: item for item in (previous_review or {}).get("candidate_pool", [])
    }
    candidates: list[dict[str, Any]] = []

    early = analyses.get("early-signal-tracker", {})
    for item in early.get("directions", []):
        metrics = _candidate_metrics(item.get("evidence_ids", []), evidence_by_id, as_of)
        metrics.update({
            "source_count": item.get("source_count", metrics["source_count"]),
            "family_count": item.get("family_count", len(metrics["source_types"])),
            "technical_family_count": item.get("technical_family_count", 0),
        })
        candidates.append({
            "id": f"early:{item['id']}",
            "origin": "early-signal",
            "title": item["title"],
            "description": item["hypothesis"],
            "source_analysis": f"early-signal-tracker/{item['id']}",
            "theme_ids": item.get("theme_ids", []),
            "evidence_ids": item.get("evidence_ids", []),
            "stage": item.get("stage"),
            "movement": item.get("movement", "steady"),
            "metrics": metrics,
        })

    for analysis_id, origin in (("expert-pulse", "expert-finding"), ("operator-narratives", "operator-narrative")):
        for item in analyses.get(analysis_id, {}).get("findings", []):
            metrics = _candidate_metrics(item.get("evidence_ids", []), evidence_by_id, as_of)
            candidates.append({
                "id": f"{origin}:{item['id']}",
                "origin": origin,
                "title": item["title"],
                "description": item.get("analysis", item.get("why_it_matters", "")),
                "source_analysis": f"{analysis_id}/{item['id']}",
                "theme_ids": item.get("theme_ids", []),
                "evidence_ids": item.get("evidence_ids", []),
                "strength": item.get("strength"),
                "movement": "new" if metrics["recent_evidence_count"] else "steady",
                "metrics": metrics,
            })

    movements = {item["theme_id"]: item for item in research.get("weekly", {}).get("movements", [])}
    for item in research.get("themes", []):
        metrics = _candidate_metrics(item.get("evidence_ids", []), evidence_by_id, as_of)
        movement = movements.get(item["id"], {})
        candidates.append({
            "id": f"theme:{item['id']}",
            "origin": "cross-source-theme",
            "title": item["name"],
            "description": item["definition"],
            "source_analysis": f"themes/{item['id']}",
            "theme_ids": [item["id"]],
            "evidence_ids": item.get("evidence_ids", [])[:20],
            "stage": item.get("maturity"),
            "movement": movement.get("direction", "steady"),
            "metrics": {
                **metrics,
                "evidence_count": item.get("evidence_count", metrics["evidence_count"]),
                "source_count": item.get("source_count", metrics["source_count"]),
                "family_count": len(metrics["source_types"]),
                "trend_score": (item.get("score") or {}).get("total"),
            },
        })

    for candidate in candidates:
        requirement = _linked_requirement(candidate["source_analysis"], requirements)
        adjudication = adjudications.get(candidate["id"])
        linked_requirements = []
        if requirement:
            linked_requirements.append(requirement)
        for requirement_id in (adjudication or {}).get("requirement_ids", []):
            resolved = requirements_by_id.get(requirement_id)
            if resolved and resolved["id"] not in {item["id"] for item in linked_requirements}:
                linked_requirements.append(resolved)
        candidate["linked_requirements"] = [
            {"id": item["id"], "title": item["title"], "maturity": item["maturity"]}
            for item in linked_requirements
        ]
        candidate["linked_requirement"] = candidate["linked_requirements"][0] if linked_requirements else None
        candidate["priority"] = _priority(candidate, bool(linked_requirements))
        candidate["change_reasons"] = _material_changes(
            candidate,
            previous_by_id.get(candidate["id"]),
            config["material_change_thresholds"],
        )
        candidate["materially_changed"] = bool(candidate["change_reasons"])
        if adjudication:
            reviewed = adjudication["reviewed_state"]
            adjudication_current = (
                candidate.get("stage") == reviewed.get("stage")
                and candidate.get("movement") == reviewed.get("movement")
                and candidate["metrics"]["evidence_count"] - reviewed["evidence_count"]
                < config["material_change_thresholds"]["evidence_count_delta"]
                and candidate["metrics"]["source_count"] - reviewed["source_count"]
                < config["material_change_thresholds"]["source_count_delta"]
            )
            candidate["adjudication"] = {
                key: value for key, value in adjudication.items() if key != "reviewed_state"
            }
            candidate["adjudication"]["status"] = "current" if adjudication_current else "revisit-required"
        else:
            candidate["adjudication"] = None
        candidate["review_action"] = (
            candidate["adjudication"]["outcome"]
            if candidate["adjudication"] and candidate["adjudication"]["status"] == "current"
            else "review-existing-requirement" if linked_requirements else "assess-new-requirement"
        )

    return sorted(candidates, key=lambda item: (-item["priority"]["total"], item["title"]))


def _select_queue(candidates: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    eligible = [
        item for item in candidates
        if item["materially_changed"]
        and (item.get("adjudication") or {}).get("status") != "current"
        and (item["priority"]["total"] >= config["minimum_priority_score"] or item["linked_requirement"])
    ]
    queue = []
    origin_counts: Counter[str] = Counter()
    linked_candidates = [item for item in eligible if item["linked_requirement"]]
    unlinked_candidates = [item for item in eligible if not item["linked_requirement"]]
    for candidate in [*linked_candidates, *unlinked_candidates]:
        if not candidate["linked_requirement"] and origin_counts[candidate["origin"]] >= 4:
            continue
        queue.append(candidate)
        origin_counts[candidate["origin"]] += 1
        if len(queue) == config["maximum_assessment_queue"]:
            break
    for rank, candidate in enumerate(queue, 1):
        candidate["queue_rank"] = rank
    return queue


def _requirement_changes(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    prior = {item["id"]: item for item in (previous or {}).get("requirements", [])}
    rank = {name: index for index, name in enumerate(MATURITY_ORDER)}
    changes = []
    for requirement in current.get("requirements", []):
        old = prior.get(requirement["id"])
        if not old:
            change_type = "baseline" if previous is None else "added"
            explanation = (
                "Added to the first tracked Operating Model baseline."
                if previous is None
                else "Added after formal candidate adjudication under the evidence policy."
            )
            previous_maturity = None
        elif old["maturity"] != requirement["maturity"]:
            change_type = "promoted" if rank[requirement["maturity"]] > rank[old["maturity"]] else "demoted"
            explanation = f"Maturity changed from {old['maturity']} to {requirement['maturity']}."
            previous_maturity = old["maturity"]
        elif len(old.get("evidence", [])) != len(requirement.get("evidence", [])):
            change_type = "evidence-updated"
            explanation = f"Linked evidence changed from {len(old.get('evidence', []))} to {len(requirement.get('evidence', []))} records without changing maturity."
            previous_maturity = old["maturity"]
        else:
            change_type = "unchanged"
            explanation = "No maturity or linked-evidence change this cycle."
            previous_maturity = old["maturity"]
        changes.append({
            "id": requirement["id"],
            "title": requirement["title"],
            "change_type": change_type,
            "previous_maturity": previous_maturity,
            "current_maturity": requirement["maturity"],
            "explanation": explanation,
        })
    return changes


def _verification_coverage(
    research: dict[str, Any],
    config: dict[str, Any],
    previous_review: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    evidence = research.get("evidence", [])
    source_by_id = {item["id"]: item for item in research.get("sources", [])}
    previous = {
        item["id"]: set(item.get("evidence_ids", []))
        for item in (previous_review or {}).get("verification_families", [])
    }
    output = []
    for definition in config.get("verification_families", []):
        source_ids = set(definition.get("source_ids", []))
        source_types = set(definition.get("source_types", []))
        terms = [term.casefold() for term in definition.get("terms", [])]
        matched = []
        for item in evidence:
            if source_ids and item.get("source_id") not in source_ids:
                continue
            if source_types and item.get("source_type") not in source_types:
                continue
            searchable = f"{item.get('title', '')} {item.get('summary', '')}".casefold()
            if terms and not any(term in searchable for term in terms):
                continue
            matched.append(item)
        matched.sort(key=lambda item: (item.get("published_at", ""), item["id"]), reverse=True)
        all_ids = [item["id"] for item in matched]
        new_ids = set(all_ids).difference(previous.get(definition["id"], set()))
        contributing_sources = sorted({item["source_id"] for item in matched})
        output.append({
            **definition,
            "status": "active" if matched else "gap",
            "record_count": len(matched),
            "source_count": len(contributing_sources),
            "source_ids": contributing_sources,
            "source_names": [source_by_id.get(source_id, {}).get("name", source_id) for source_id in contributing_sources],
            "new_record_count": len(new_ids),
            "evidence_ids": all_ids,
            "sample_evidence_ids": all_ids[: definition.get("evidence_limit", 8)],
            "boundary": "Supporting verification signal only; maturity still requires case-level review under the formal evidence policy.",
        })
    return output


def build_weekly_review(
    research: dict[str, Any],
    operating_model: dict[str, Any],
    previous_operating_model: dict[str, Any] | None,
    previous_review: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    candidates = _candidate_pool(research, operating_model, previous_review, config)
    queue = _select_queue(candidates, config)
    adjudications = [
        {
            "candidate_id": item["id"],
            "title": item["title"],
            "origin": item["origin"],
            "source_analysis": item["source_analysis"],
            "stage": item.get("stage"),
            "metrics": item["metrics"],
            "linked_requirements": item.get("linked_requirements", []),
            **item["adjudication"],
        }
        for item in candidates
        if item.get("adjudication")
    ]
    changes = _requirement_changes(operating_model, previous_operating_model)
    added_requirement_ids = {
        item["id"] for item in changes if item["change_type"] == "added"
    }
    queue = [
        item for item in queue
        if not added_requirement_ids.intersection(
            requirement["id"] for requirement in item.get("linked_requirements", [])
        )
    ]
    for rank, candidate in enumerate(queue, 1):
        candidate["queue_rank"] = rank
    verification = _verification_coverage(research, config, previous_review)
    changed_requirements = [item for item in changes if item["change_type"] not in {"unchanged", "baseline"}]
    origin_counts = dict(Counter(item["origin"] for item in candidates))
    baseline = previous_review is None
    candidate_noun = "candidate" if len(queue) == 1 else "candidates"
    candidate_verb = "remains" if len(queue) == 1 else "remain"
    same_cycle = bool(previous_review and previous_review.get("meta", {}).get("as_of") == research["weekly"]["as_of"])
    if (
        same_cycle
        and not any(item["materially_changed"] for item in candidates)
        and not changed_requirements
        and not any(item["new_record_count"] for item in verification)
    ):
        preserved = {**previous_review, "meta": {**previous_review["meta"]}}
        preserved["meta"]["generated_at"] = research["meta"]["generated_at"]
        preserved["meta"]["idempotent_regeneration"] = True
        return preserved

    return {
        "meta": {
            "title": "Weekly Operating Model Review",
            "generated_at": research["meta"]["generated_at"],
            "as_of": research["weekly"]["as_of"],
            "policy_version": config["version"],
            "baseline_cycle": baseline,
            "candidate_pool_count": len(candidates),
            "candidate_origin_counts": origin_counts,
            "materially_changed_count": sum(item["materially_changed"] for item in candidates),
            "assessment_queue_count": len(queue),
            "adjudication_count": len(adjudications),
            "requirement_change_count": len(changed_requirements),
        },
        "summary": {
            "headline": (
                f"{len(adjudications)} candidate decisions are recorded; {len(queue)} {candidate_noun} {candidate_verb} in the bounded assessment queue."
                if adjudications
                else f"{len(queue)} {candidate_noun} require assessment from a {len(candidates)}-item cross-source pool."
                if queue else "No candidate crossed the material-change review boundary this week."
            ),
            "interpretation": "Candidate priority controls analyst attention only. It cannot create, promote, or demote an Operating Model requirement.",
        },
        "selection_policy": {
            "maximum_queue": config["maximum_assessment_queue"],
            "minimum_priority_score": config["minimum_priority_score"],
            "components": config["priority_components"],
            "material_change_thresholds": config["material_change_thresholds"],
            "commitment_boundary": "A reviewer must update the calibrated case record before the Operating Model can change.",
        },
        "candidate_pool": candidates,
        "adjudications": adjudications,
        "assessment_queue": queue,
        "requirement_changes": changes,
        "verification_families": verification,
    }


def weekly_review_markdown(payload: dict[str, Any]) -> str:
    meta = payload["meta"]
    lines = [
        f"# Weekly Operating Model Review — {meta['as_of']}",
        "",
        payload["summary"]["headline"],
        "",
        f"> {payload['summary']['interpretation']}",
        "",
        "## Adjudicated candidates",
        "",
        "| Candidate | Outcome | Linked requirement | Decision |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload.get("adjudications", []):
        linked = ", ".join(requirement["title"] for requirement in item.get("linked_requirements", [])) or "None"
        lines.append(f"| {item['title']} | {item['outcome']} | {linked} | {item['decision']} |")
    if not payload.get("adjudications"):
        lines.append("| — | No adjudications recorded | — | — |")
    lines.extend([
        "",
        "## Assessment queue",
        "",
        "| Rank | Candidate | Origin | Priority | Action |",
        "| ---: | --- | --- | ---: | --- |",
    ])
    for item in payload["assessment_queue"]:
        lines.append(f"| {item['queue_rank']} | {item['title']} | {item['origin']} | {item['priority']['total']} | {item['review_action']} |")
    if not payload["assessment_queue"]:
        lines.append("| — | No material candidate changes | — | — | — |")
    lines.extend(["", "## Operating Model changes", ""])
    meaningful = [item for item in payload["requirement_changes"] if item["change_type"] != "unchanged"]
    for item in meaningful:
        lines.append(f"- **{item['title']}** — {item['change_type']}: {item['explanation']}")
    if not meaningful:
        lines.append("- No maturity or linked-evidence changes this cycle.")
    lines.extend(["", "## Verification coverage", ""])
    for item in payload["verification_families"]:
        lines.append(f"- **{item['title']}** — {item['record_count']} records across {item['source_count']} sources; {item['new_record_count']} newly observed in this review history.")
    lines.extend([
        "",
        "## Commitment boundary",
        "",
        payload["selection_policy"]["commitment_boundary"],
        "",
    ])
    return "\n".join(lines)


def write_weekly_review(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(weekly_review_markdown(payload), encoding="utf-8")
