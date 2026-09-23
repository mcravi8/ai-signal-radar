from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .export_public import PublicDataError, validate_public_payload
from .normalize import canonical_url, compact_text


DISCOVERY_STATES = {"spark", "candidate", "approved", "merged", "rejected", "dormant"}
TERMINAL_ACTIONS = {
    "approved": "track",
    "merged": "merge",
    "rejected": "reject",
    "dormant": "dormancy",
}


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_discovery_policy(policy: dict[str, Any]) -> None:
    required = {
        "version",
        "purpose",
        "states",
        "state_transitions",
        "review_actions",
        "record_contract",
        "eligibility",
        "state_entry_gates",
        "source_families",
        "technical_source_families",
    }
    missing = required.difference(policy)
    if missing:
        raise ValueError(f"Discovery policy is missing: {', '.join(sorted(missing))}")
    if policy["version"] != 1:
        raise ValueError("Unsupported discovery policy version")
    if set(policy["states"]) != DISCOVERY_STATES:
        raise ValueError("Discovery states do not match the locked contract")
    if set(policy["state_transitions"]) != DISCOVERY_STATES:
        raise ValueError("Every discovery state must define transitions")
    for state, targets in policy["state_transitions"].items():
        unknown = set(targets).difference(DISCOVERY_STATES)
        if unknown:
            raise ValueError(f"Unknown transition from {state}: {sorted(unknown)}")
        if policy["states"][state].get("terminal") and targets:
            raise ValueError(f"Terminal discovery state cannot have transitions: {state}")
    if set(policy["review_actions"].values()).difference(DISCOVERY_STATES):
        raise ValueError("A discovery review action points to an unknown state")

    contract = policy["record_contract"]
    contract_required = {
        "required_fields",
        "required_metric_fields",
        "list_fields",
        "observation_fields",
        "inference_fields",
        "rules",
    }
    if contract_required.difference(contract):
        raise ValueError("Discovery record contract is incomplete")
    required_fields = set(contract["required_fields"])
    labelled_fields = set(contract["observation_fields"]) | set(contract["inference_fields"])
    if not labelled_fields.issubset(required_fields):
        raise ValueError("Observation and inference labels must reference required record fields")
    if set(contract["observation_fields"]).intersection(contract["inference_fields"]):
        raise ValueError("Observation and inference fields must remain disjoint")

    eligibility = policy["eligibility"]
    eligibility_required = {
        "lookback_days",
        "future_tolerance_days",
        "required_fields",
        "required_content_fields_any",
        "accepted_change_types",
        "fingerprint_fields",
        "exclusion_reason_codes",
        "deduplication",
        "candidate_contribution_caps",
    }
    missing_eligibility = eligibility_required.difference(eligibility)
    if missing_eligibility:
        raise ValueError(f"Discovery eligibility is missing: {', '.join(sorted(missing_eligibility))}")
    if eligibility["lookback_days"] < 7:
        raise ValueError("Discovery lookback must cover at least one weekly cycle")
    if set(eligibility["accepted_change_types"]) != {"new-record", "materially-changed"}:
        raise ValueError("Discovery must be limited to new or materially changed records")
    caps = eligibility["candidate_contribution_caps"]
    if caps.get("per_source", 0) < 1 or caps.get("per_publisher", 0) < 1:
        raise ValueError("Discovery contribution caps must be positive")
    candidate_gate = policy["state_entry_gates"].get("candidate", {})
    if candidate_gate.get("minimum_evidence_count", 0) < 3:
        raise ValueError("A discovery Candidate must require at least three evidence records")
    if candidate_gate.get("minimum_source_count", 0) < 3:
        raise ValueError("A discovery Candidate must require at least three sources")
    if candidate_gate.get("minimum_source_family_count", 0) < 2:
        raise ValueError("A discovery Candidate must require at least two source families")
    dominant_cap = candidate_gate.get("maximum_dominant_publisher_share", 1)
    if not 0 < dominant_cap <= 0.5:
        raise ValueError("A discovery Candidate cannot permit one publisher to hold a majority")


def validate_discovery_record(record: dict[str, Any], policy: dict[str, Any]) -> None:
    validate_discovery_policy(policy)
    contract = policy["record_contract"]
    missing = [field for field in contract["required_fields"] if field not in record]
    if missing:
        raise ValueError(f"Discovery record is missing: {', '.join(missing)}")
    if record["state"] not in DISCOVERY_STATES:
        raise ValueError(f"Unknown discovery state: {record['state']}")

    for field in ("id", "title", "observed_pattern", "hypothesis", "why_now", "novelty"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"Discovery record requires non-empty {field}")
    for field in contract["list_fields"]:
        if not isinstance(record[field], list):
            raise ValueError(f"Discovery record {field} must be a list")
        if len(record[field]) != len(set(record[field])):
            raise ValueError(f"Discovery record {field} must not contain duplicates")
    for field in ("evidence_ids", "source_ids", "source_family_ids", "concepts"):
        if not record[field]:
            raise ValueError(f"Discovery record requires at least one {field}")
    for field in ("alternative_explanations", "confirmation_conditions", "invalidation_conditions"):
        if not record[field] or not all(isinstance(value, str) and value.strip() for value in record[field]):
            raise ValueError(f"Discovery record requires a non-empty {field}")

    first_seen = _parse_datetime(record["first_seen"])
    last_seen = _parse_datetime(record["last_seen"])
    if not first_seen or not last_seen or first_seen > last_seen:
        raise ValueError("Discovery record observation dates are invalid")

    metrics = record["metrics"]
    missing_metrics = [field for field in contract["required_metric_fields"] if field not in metrics]
    if missing_metrics:
        raise ValueError(f"Discovery metrics are missing: {', '.join(missing_metrics)}")
    count_fields = [field for field in contract["required_metric_fields"] if field != "dominant_publisher_share"]
    if any(not isinstance(metrics[field], int) or metrics[field] < 0 for field in count_fields):
        raise ValueError("Discovery metric counts must be non-negative integers")
    dominant_share = metrics["dominant_publisher_share"]
    if not isinstance(dominant_share, (int, float)) or not 0 <= dominant_share <= 1:
        raise ValueError("dominant_publisher_share must be between zero and one")
    if metrics["evidence_count"] != len(record["evidence_ids"]):
        raise ValueError("evidence_count must match evidence_ids")
    if metrics["source_count"] != len(record["source_ids"]):
        raise ValueError("source_count must match source_ids")
    if metrics["source_family_count"] != len(record["source_family_ids"]):
        raise ValueError("source_family_count must match source_family_ids")
    if metrics["independent_event_count"] > metrics["evidence_count"]:
        raise ValueError("independent_event_count cannot exceed evidence_count")
    if metrics["technical_record_count"] > metrics["evidence_count"]:
        raise ValueError("technical_record_count cannot exceed evidence_count")

    eligibility = record["eligibility"]
    if eligibility.get("decision") not in {"eligible", "excluded"}:
        raise ValueError("Discovery eligibility decision must be eligible or excluded")
    if not isinstance(eligibility.get("reason_codes"), list):
        raise ValueError("Discovery eligibility reason_codes must be a list")
    entry_state = discovery_entry_state(
        metrics,
        policy,
        novelty_reviewed=bool(eligibility.get("novelty_reviewed")),
    )
    if record["state"] in {"candidate", "approved"} and entry_state != "candidate":
        raise ValueError(f"Discovery state {record['state']} requires the Candidate entry gate")
    if record["state"] == "spark" and entry_state not in {"spark", "candidate"}:
        raise ValueError("Discovery state spark requires the Spark entry gate")

    review = record["review"]
    if review.get("status") not in {"pending", "decided"}:
        raise ValueError("Discovery review status must be pending or decided")
    action = review.get("action")
    if action is not None and action not in policy["review_actions"]:
        raise ValueError(f"Unknown discovery review action: {action}")
    expected_action = TERMINAL_ACTIONS.get(record["state"])
    if expected_action and (review.get("status") != "decided" or action != expected_action):
        raise ValueError(f"Discovery state {record['state']} requires review action {expected_action}")


def discovery_entry_state(
    metrics: dict[str, Any],
    policy: dict[str, Any],
    *,
    novelty_reviewed: bool = False,
) -> str | None:
    """Return the highest mechanical discovery state; never returns approved."""
    validate_discovery_policy(policy)
    candidate = policy["state_entry_gates"]["candidate"]
    candidate_met = (
        metrics.get("evidence_count", 0) >= candidate["minimum_evidence_count"]
        and metrics.get("independent_event_count", 0) >= candidate["minimum_independent_event_count"]
        and metrics.get("source_count", 0) >= candidate["minimum_source_count"]
        and metrics.get("source_family_count", 0) >= candidate["minimum_source_family_count"]
        and metrics.get("dominant_publisher_share", 1) <= candidate["maximum_dominant_publisher_share"]
    )
    if candidate_met:
        return "candidate"

    spark = policy["state_entry_gates"]["spark"]["any_of"]
    cross_source = spark["cross_source"]
    if (
        metrics.get("evidence_count", 0) >= cross_source["minimum_evidence_count"]
        and metrics.get("source_count", 0) >= cross_source["minimum_source_count"]
    ):
        return "spark"
    technical = spark["technical_seed"]
    if (
        metrics.get("evidence_count", 0) >= technical["minimum_evidence_count"]
        and metrics.get("technical_record_count", 0) >= technical["minimum_technical_record_count"]
        and (not technical.get("requires_manual_novelty_review") or novelty_reviewed)
    ):
        return "spark"
    return None


def evidence_fingerprint(item: dict[str, Any], policy: dict[str, Any]) -> str:
    fields = policy["eligibility"]["fingerprint_fields"]
    payload = {field: item.get(field) for field in fields}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _source_rank(source: dict[str, Any], policy: dict[str, Any]) -> int:
    preferred = policy["eligibility"]["deduplication"]["prefer_source_channels"]
    channel = source.get("channel", "")
    try:
        return preferred.index(channel)
    except ValueError:
        return len(preferred)


def _published_rank(item: dict[str, Any]) -> int:
    published = _parse_datetime(item.get("published_at", ""))
    return published.toordinal() if published else 0


def _title_key(item: dict[str, Any]) -> str:
    return compact_text(item.get("title", "")).casefold()


def _event_duplicate(
    item: dict[str, Any],
    accepted: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any] | None:
    dedupe = policy["eligibility"]["deduplication"]
    event_field = dedupe["explicit_event_id_field"]
    event_id = item.get("metadata", {}).get(event_field) or item.get(event_field)
    item_url = canonical_url(item.get("url", ""))
    title = _title_key(item)
    published = _parse_datetime(item.get("published_at", ""))
    title_window = timedelta(days=dedupe["same_title_window_days"])
    for existing in accepted:
        existing_event_id = existing.get("metadata", {}).get(event_field) or existing.get(event_field)
        if event_id and existing_event_id and event_id == existing_event_id:
            return existing
        existing_url = canonical_url(existing.get("url", ""))
        if item_url and existing_url and item_url == existing_url:
            return existing
        existing_published = _parse_datetime(existing.get("published_at", ""))
        if title and title == _title_key(existing) and published and existing_published:
            if abs(published - existing_published) <= title_window:
                return existing
    return None


def select_eligible_evidence(
    items: Iterable[dict[str, Any]],
    sources: Iterable[dict[str, Any]],
    policy: dict[str, Any],
    *,
    as_of: datetime,
    previous_fingerprints: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Select bounded discovery inputs without interpreting or clustering them."""
    validate_discovery_policy(policy)
    as_of = as_of.astimezone(timezone.utc)
    eligibility = policy["eligibility"]
    source_by_id = {source["id"]: source for source in sources}
    fingerprints: dict[str, str] = {}
    prepared: list[tuple[dict[str, Any], str]] = []
    excluded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def exclude(item: dict[str, Any], reason: str, **extra: Any) -> None:
        excluded.append({"evidence_id": item.get("id", ""), "reason_codes": [reason], **extra})

    for item in items:
        item_id = item.get("id", "")
        if item_id in seen_ids:
            exclude(item, "duplicate-record")
            continue
        if item_id:
            seen_ids.add(item_id)
        missing = [field for field in eligibility["required_fields"] if not item.get(field)]
        if missing:
            exclude(item, "missing-required-field", missing_fields=missing)
            continue
        if not any(compact_text(str(item.get(field, ""))) for field in eligibility["required_content_fields_any"]):
            exclude(item, "missing-content")
            continue
        source = source_by_id.get(item["source_id"])
        if not source:
            exclude(item, "unknown-source")
            continue
        if eligibility.get("require_enabled_source") and not source.get("enabled", False):
            exclude(item, "disabled-source")
            continue
        if eligibility.get("require_public_safe_record"):
            try:
                validate_public_payload({"items": [item]})
            except PublicDataError:
                exclude(item, "not-public-safe")
                continue
        published = _parse_datetime(item["published_at"])
        if not published:
            exclude(item, "invalid-date")
            continue
        if published > as_of + timedelta(days=eligibility["future_tolerance_days"]):
            exclude(item, "future-dated")
            continue
        if published <= as_of - timedelta(days=eligibility["lookback_days"]):
            exclude(item, "outside-window")
            continue

        fingerprint = evidence_fingerprint(item, policy)
        fingerprints[item_id] = fingerprint
        previous = (previous_fingerprints or {}).get(item_id)
        if previous_fingerprints is not None and previous == fingerprint:
            exclude(item, "unchanged")
            continue
        change_type = "materially-changed" if previous is not None else "new-record"
        prepared.append((item, change_type))

    prepared.sort(
        key=lambda pair: (
            _source_rank(source_by_id[pair[0]["source_id"]], policy),
            -_published_rank(pair[0]),
            pair[0]["id"],
        )
    )
    accepted_items: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for item, change_type in prepared:
        duplicate = _event_duplicate(item, accepted_items, policy)
        if duplicate:
            exclude(item, "duplicate-event", duplicate_of=duplicate["id"])
            continue
        accepted_items.append(item)
        accepted.append({"evidence": item, "change_type": change_type, "fingerprint": fingerprints[item["id"]]})

    return {
        "eligible": accepted,
        "excluded": sorted(excluded, key=lambda value: (value["evidence_id"], value["reason_codes"])),
        "fingerprints": fingerprints,
    }


def cap_candidate_contributions(
    items: Iterable[dict[str, Any]],
    sources: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Apply independence caps inside one proposed cluster, not globally."""
    validate_discovery_policy(policy)
    source_by_id = {source["id"]: source for source in sources}
    caps = policy["eligibility"]["candidate_contribution_caps"]
    source_counts: Counter[str] = Counter()
    publisher_counts: Counter[str] = Counter()
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    ranked = sorted(
        items,
        key=lambda item: (
            _source_rank(source_by_id.get(item.get("source_id"), {}), policy),
            -_published_rank(item),
            item.get("id") or item.get("evidence_id", ""),
        ),
    )
    for item in ranked:
        source_id = item.get("source_id", "")
        source = source_by_id.get(source_id, {})
        publisher_id = source.get("publisher_id") or source_id
        reasons = []
        if source_counts[source_id] >= caps["per_source"]:
            reasons.append("source-cap")
        if publisher_counts[publisher_id] >= caps["per_publisher"]:
            reasons.append("publisher-cap")
        if reasons:
            excluded.append(
                {"evidence_id": item.get("id") or item.get("evidence_id", ""), "reason_codes": reasons}
            )
            continue
        kept.append(item)
        source_counts[source_id] += 1
        publisher_counts[publisher_id] += 1
    return {"kept": kept, "excluded": excluded}
