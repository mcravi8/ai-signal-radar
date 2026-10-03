from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


STATUS_FILES = {
    "public-collection": "status.json",
    "events": "event-status.json",
    "verification": "verification-status.json",
    "bluesky": "bluesky-status.json",
    "newsletters": "newsletter-status.json",
}


def _latest_status(snapshot_root: Path, filename: str) -> tuple[Path, dict[str, Any]] | None:
    matches = sorted(snapshot_root.glob(f"*/{filename}"))
    if not matches:
        return None
    path = matches[-1]
    return path, json.loads(path.read_text(encoding="utf-8"))


def _snapshot_source_counts(path: Path, filename: str) -> Counter[str]:
    item_filename = {
        "status.json": "items.jsonl",
        "event-status.json": "event-items.jsonl",
        "verification-status.json": "verification-items.jsonl",
        "bluesky-status.json": "bluesky-items.jsonl",
        "newsletter-status.json": "newsletter-items.jsonl",
    }[filename]
    item_path = path.with_name(item_filename)
    counts: Counter[str] = Counter()
    if not item_path.exists():
        return counts
    for line in item_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("source_id"):
            counts[row["source_id"]] += 1
    return counts


def _legacy_collectors(path: Path, payload: dict[str, Any], filename: str) -> list[dict[str, Any]]:
    counts = _snapshot_source_counts(path, filename)
    errors: dict[str, str] = {}
    for error in payload.get("errors", []):
        source_id, _, message = str(error).partition(":")
        errors[source_id.strip()] = message.strip() or str(error)
    source_ids = set(counts) | set(errors)
    return [
        {
            "source_id": source_id,
            "status": "failed" if source_id in errors else "healthy",
            "items": counts[source_id],
            **({"error": errors[source_id]} if source_id in errors else {}),
        }
        for source_id in sorted(source_ids)
    ]


def build_collection_health(snapshot_root: Path, sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a public-safe ledger from the newest receipt for each collector family."""
    source_state: dict[str, dict[str, Any]] = {}
    runs = []
    for run_id, filename in STATUS_FILES.items():
        latest = _latest_status(snapshot_root, filename)
        if not latest:
            continue
        path, payload = latest
        collectors = payload.get("collectors") or _legacy_collectors(path, payload, filename)
        failed = [item for item in collectors if item.get("status") == "failed"]
        run = {
            "id": run_id,
            "collected_at": payload.get("collected_at"),
            "status": "degraded" if failed else "healthy",
            "source_count": len(collectors),
            "failed_source_count": len(failed),
            "failed_source_ids": sorted(item["source_id"] for item in failed),
        }
        runs.append(run)
        for item in collectors:
            source_state[item["source_id"]] = {
                "status": item.get("status", "unknown"),
                "collected_at": payload.get("collected_at"),
                "items": item.get("items", 0),
                **({"error": item["error"]} if item.get("error") else {}),
                "run_id": run_id,
            }

    configured = {source["id"]: source for source in sources}
    for source_id, source in configured.items():
        if source_id in source_state:
            continue
        source_state[source_id] = {
            "status": "not-automated" if source.get("collection") in {None, "manual"} else "no-run-receipt",
            "collected_at": None,
            "items": 0,
            "run_id": None,
        }

    failed_sources = sorted(
        source_id for source_id, state in source_state.items()
        if state["status"] == "failed"
    )
    latest_failed_at = max(
        (source_state[source_id].get("collected_at") or "" for source_id in failed_sources),
        default="",
    ) or None
    degraded_runs = [run for run in runs if run["status"] == "degraded"]
    latest_at = max((run["collected_at"] or "" for run in runs), default="") or None
    return {
        "status": "degraded" if degraded_runs else "healthy" if runs else "not-observed",
        "latest_receipt_at": latest_at,
        "latest_failed_receipt_at": latest_failed_at,
        "failed_source_count": len(failed_sources),
        "failed_source_ids": failed_sources,
        "runs": sorted(runs, key=lambda item: (item.get("collected_at") or "", item["id"]), reverse=True),
        "sources": source_state,
        "interpretation": "Collection health reports the newest stored run receipt. Evidence recency is measured separately and does not prove that the latest collector succeeded.",
    }
