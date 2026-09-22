from __future__ import annotations

from typing import Any


PUBLIC_DIMENSIONS = {
    "technical_reality",
    "operational_adoption",
    "market_pull",
    "evidence_independence",
}


def validate_policy(policy: dict[str, Any]) -> None:
    required = {
        "version",
        "public_levels",
        "maturity_order",
        "maturity_definitions",
        "relationship_types",
        "source_role_defaults",
        "dimension_rules",
        "maturity_gates",
        "guardrails",
    }
    missing = required.difference(policy)
    if missing:
        raise ValueError(f"Evidence policy is missing: {', '.join(sorted(missing))}")
    if policy["public_levels"] != ["not-observed", "low", "moderate", "strong"]:
        raise ValueError("Public evidence levels must remain N/O, Low, Moderate, Strong")
    if policy["maturity_order"] != ["narrative", "experimental", "emerging", "established", "baseline"]:
        raise ValueError("Maturity order does not match the locked operating-model contract")
    if set(policy["maturity_definitions"]) != set(policy["maturity_order"]):
        raise ValueError("Every maturity state must have exactly one public definition")
    for maturity, definition in policy["maturity_definitions"].items():
        if not definition.get("description") or not definition.get("recommended_posture"):
            raise ValueError(f"Maturity definition is incomplete: {maturity}")
    if set(policy["dimension_rules"]) != PUBLIC_DIMENSIONS:
        raise ValueError("Evidence dimensions do not match the locked operating-model contract")
    if set(policy["maturity_gates"]) != set(policy["maturity_order"]):
        raise ValueError("Every maturity state must have exactly one gate")


def _analysis_target_exists(research: dict[str, Any], target: str) -> bool:
    analysis_id, _, child_id = target.partition("/")
    analysis = next((item for item in research.get("analyses", []) if item["id"] == analysis_id), None)
    if not analysis:
        return False
    if not child_id:
        return True
    children = [*analysis.get("directions", []), *analysis.get("findings", [])]
    return any(item.get("id") == child_id for item in children)


def validate_calibration(
    policy: dict[str, Any],
    calibration: dict[str, Any],
    research: dict[str, Any],
) -> None:
    validate_policy(policy)
    if calibration.get("policy_version") != policy["version"]:
        raise ValueError("Calibration policy version does not match the evidence policy")

    evidence_ids = {item["id"] for item in research.get("evidence", [])}
    case_ids: set[str] = set()
    level_values = set(policy["public_levels"])
    relationship_values = set(policy["relationship_types"])
    maturity_values = set(policy["maturity_order"])

    for case in calibration.get("cases", []):
        case_id = case.get("id", "")
        if not case_id or case_id in case_ids:
            raise ValueError(f"Calibration case id is missing or duplicated: {case_id!r}")
        case_ids.add(case_id)
        if not _analysis_target_exists(research, case["source_analysis"]):
            raise ValueError(f"Unknown source analysis for {case_id}: {case['source_analysis']}")
        if case.get("expected_maturity") not in maturity_values:
            raise ValueError(f"Unknown expected maturity for {case_id}")
        for field in ("title", "requirement", "description", "applicable_to", "rationale"):
            if not case.get(field):
                raise ValueError(f"Calibration case {case_id} is missing {field}")
        if len(case.get("what_it_looks_like", [])) < 2:
            raise ValueError(f"Calibration case {case_id} needs concrete operating examples")

        seen_evidence: set[str] = set()
        direct_events: set[str] = set()
        technical_events: set[str] = set()
        for link in case.get("evidence_links", []):
            evidence_id = link.get("evidence_id", "")
            if evidence_id not in evidence_ids:
                raise ValueError(f"Unknown evidence id in {case_id}: {evidence_id}")
            if evidence_id in seen_evidence:
                raise ValueError(f"Duplicated evidence id in {case_id}: {evidence_id}")
            seen_evidence.add(evidence_id)
            relationship = link.get("relationship")
            if relationship not in relationship_values:
                raise ValueError(f"Unknown relationship in {case_id}: {relationship}")
            dimensions = set(link.get("dimensions", []))
            if not dimensions.issubset(PUBLIC_DIMENSIONS):
                raise ValueError(f"Unknown evidence dimension in {case_id}: {sorted(dimensions - PUBLIC_DIMENSIONS)}")
            if relationship == "excluded" and not link.get("exclusion_reason"):
                raise ValueError(f"Excluded evidence requires a reason in {case_id}: {evidence_id}")
            if policy["relationship_types"][relationship]["promotion_eligible"]:
                direct_events.add(link["event_id"])
                if "technical_reality" in dimensions:
                    technical_events.add(link["event_id"])

        assessments = case.get("assessments", {})
        for dimension in PUBLIC_DIMENSIONS:
            if assessments.get(dimension) not in level_values:
                raise ValueError(f"Invalid {dimension} level in {case_id}")
        if assessments.get("confidence") not in {"low", "moderate", "high"}:
            raise ValueError(f"Invalid confidence in {case_id}")
        if assessments.get("concentration") not in {"low", "moderate", "high"}:
            raise ValueError(f"Invalid concentration in {case_id}")

        gate_inputs = case.get("gate_inputs", {})
        has_counterevidence = any(
            link.get("relationship") == "counterevidence"
            for link in case.get("evidence_links", [])
        )
        if gate_inputs.get("counterevidence_reviewed") and not has_counterevidence:
            raise ValueError(f"Counterevidence review requires a linked counterevidence record in {case_id}")
        if assessments["concentration"] == "high" and assessments["evidence_independence"] != "low":
            raise ValueError(f"High concentration must cap evidence independence at low in {case_id}")
        if assessments["concentration"] == "high" and assessments["confidence"] == "high":
            raise ValueError(f"High concentration must cap confidence at moderate in {case_id}")
        if not gate_inputs.get("counterevidence_reviewed") and assessments["confidence"] == "high":
            raise ValueError(f"Missing counterevidence review must cap confidence at moderate in {case_id}")
        if gate_inputs.get("qualifying_events") != len(direct_events):
            raise ValueError(f"qualifying_events does not match deduplicated direct-support events in {case_id}")
        if gate_inputs.get("technical_artifacts") != len(technical_events):
            raise ValueError(f"technical_artifacts does not match direct technical events in {case_id}")


def _gate_result(
    policy: dict[str, Any],
    case: dict[str, Any],
    maturity: str,
    prior_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    gate = policy["maturity_gates"][maturity]
    assessments = case["assessments"]
    inputs = case["gate_inputs"]
    level_rank = {name: index for index, name in enumerate(policy["public_levels"])}
    failures: list[str] = []

    inherited = gate.get("inherits")
    if inherited and not prior_results[inherited]["passed"]:
        failures.append(f"requires {inherited}")
    for dimension, minimum in gate.get("minimum_levels", {}).items():
        actual = assessments[dimension]
        if level_rank[actual] < level_rank[minimum]:
            failures.append(f"{dimension} is {actual}; requires {minimum}")
    for key, minimum in gate.items():
        if not key.startswith("minimum_") or key == "minimum_levels":
            continue
        input_name = key.removeprefix("minimum_")
        actual = inputs.get(input_name, 0)
        if actual < minimum:
            failures.append(f"{input_name} is {actual}; requires {minimum}")
    for flag, required in gate.get("required_flags", {}).items():
        actual = inputs.get(flag, False)
        if actual is not required:
            failures.append(f"{flag} is {actual}; requires {required}")
    return {"passed": not failures, "failures": failures}


def evaluate_case(policy: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    maturity = "narrative"
    for candidate in policy["maturity_order"]:
        results[candidate] = _gate_result(policy, case, candidate, results)
        if results[candidate]["passed"]:
            maturity = candidate
    return {
        "id": case["id"],
        "requirement": case["requirement"],
        "maturity": maturity,
        "expected_maturity": case["expected_maturity"],
        "matches_expected": maturity == case["expected_maturity"],
        "assessments": case["assessments"],
        "gate_results": results,
        "rationale": case["rationale"],
        "evidence_gaps": case.get("evidence_gaps", []),
    }


def run_calibration(
    policy: dict[str, Any],
    calibration: dict[str, Any],
    research: dict[str, Any],
) -> list[dict[str, Any]]:
    validate_calibration(policy, calibration, research)
    return [evaluate_case(policy, case) for case in calibration["cases"]]


def build_operating_model(
    policy: dict[str, Any],
    calibration: dict[str, Any],
    research: dict[str, Any],
) -> dict[str, Any]:
    results = run_calibration(policy, calibration, research)
    result_by_id = {result["id"]: result for result in results}
    evidence_by_id = {item["id"]: item for item in research.get("evidence", [])}
    source_by_id = {item["id"]: item for item in research.get("sources", [])}
    maturity_counts = {maturity: 0 for maturity in policy["maturity_order"]}
    requirements = []

    for case in calibration["cases"]:
        result = result_by_id[case["id"]]
        maturity_counts[result["maturity"]] += 1
        next_gate = next(
            (
                {"maturity": maturity, "failures": gate["failures"]}
                for maturity, gate in result["gate_results"].items()
                if not gate["passed"]
            ),
            None,
        )
        linked_evidence = []
        for link in case["evidence_links"]:
            item = evidence_by_id[link["evidence_id"]]
            source = source_by_id.get(item.get("source_id"), {})
            linked_evidence.append(
                {
                    "id": item["id"],
                    "event_id": link["event_id"],
                    "title": item.get("title", "Untitled evidence"),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at"),
                    "source_id": item.get("source_id"),
                    "source_name": source.get("name", item.get("source_id", "Unknown source")),
                    "source_type": item.get("source_type", "unknown"),
                    "relationship": link["relationship"],
                    "dimensions": link.get("dimensions", []),
                    "exclusion_reason": link.get("exclusion_reason"),
                }
            )
        requirements.append(
            {
                "id": case["id"],
                "title": case["title"],
                "requirement": case["requirement"],
                "description": case["description"],
                "what_it_looks_like": case["what_it_looks_like"],
                "applicable_to": case["applicable_to"],
                "source_analysis": case["source_analysis"],
                "maturity": result["maturity"],
                "confidence": case["assessments"]["confidence"],
                "concentration": case["assessments"]["concentration"],
                "assessments": {
                    dimension: case["assessments"][dimension]
                    for dimension in sorted(PUBLIC_DIMENSIONS)
                },
                "rationale": case["rationale"],
                "next_gate": next_gate,
                "evidence_gaps": case.get("evidence_gaps", []),
                "evidence": linked_evidence,
                "gate_inputs": case["gate_inputs"],
            }
        )

    maturity_rank = {name: index for index, name in enumerate(policy["maturity_order"])}
    requirements.sort(key=lambda item: (-maturity_rank[item["maturity"]], item["title"]))
    return {
        "meta": {
            "title": policy["name"],
            "generated_at": research.get("meta", {}).get("generated_at"),
            "as_of": calibration.get("as_of"),
            "policy_version": policy["version"],
            "requirement_count": len(requirements),
            "maturity_counts": maturity_counts,
        },
        "purpose": policy["purpose"],
        "maturity_order": policy["maturity_order"],
        "maturity_definitions": policy["maturity_definitions"],
        "dimension_rules": policy["dimension_rules"],
        "relationship_types": policy["relationship_types"],
        "guardrails": policy["guardrails"],
        "requirements": requirements,
        "boundary": "Early Signal Tracker states describe attention and corroboration. Operating requirement maturity describes whether technical, operational, market, and independent evidence justify action.",
    }


def format_calibration(results: list[dict[str, Any]]) -> str:
    lines = []
    for result in results:
        next_gate = next(
            (
                (name, gate)
                for name, gate in result["gate_results"].items()
                if not gate["passed"]
            ),
            None,
        )
        line = f"{result['id']}: {result['maturity']}"
        if next_gate:
            name, gate = next_gate
            line += f"; blocked at {name} by " + "; ".join(gate["failures"])
        lines.append(line)
    return "\n".join(lines)
