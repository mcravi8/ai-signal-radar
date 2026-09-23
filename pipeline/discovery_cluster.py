from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from .discovery import (
    cap_candidate_contributions,
    discovery_entry_state,
    validate_discovery_policy,
    validate_discovery_record,
)
from .normalize import compact_text, slugify


def validate_clustering_policy(policy: dict[str, Any]) -> None:
    required = {
        "version",
        "method",
        "purpose",
        "anchors",
        "merging",
        "clusters",
        "known_comparison",
        "record_generation",
    }
    missing = required.difference(policy)
    if missing:
        raise ValueError(f"Discovery clustering policy is missing: {', '.join(sorted(missing))}")
    if policy["version"] != 1 or policy["method"] != "lexical-anchor-overlap-v1":
        raise ValueError("Unsupported discovery clustering policy")
    anchors = policy["anchors"]
    if anchors["minimum_document_count"] < 2 or anchors["minimum_source_count"] < 2:
        raise ValueError("Discovery anchors must recur across at least two records and sources")
    if not 0 < anchors["maximum_document_fraction"] < 1:
        raise ValueError("Anchor maximum_document_fraction must be between zero and one")
    if not set(anchors["structural_kinds"]).issubset({*anchors["allowed_kinds"], "relationship"}):
        raise ValueError("Structural discovery anchor kinds are invalid")
    if not set(anchors["entity_kinds"]).issubset(anchors["allowed_kinds"]):
        raise ValueError("Entity discovery anchor kinds are invalid")
    merging = policy["merging"]
    if merging["minimum_shared_documents"] < 2:
        raise ValueError("Cluster merging must require at least two shared records")
    if not 0 < merging["minimum_jaccard"] <= 1 or not 0 < merging["minimum_containment"] <= 1:
        raise ValueError("Cluster overlap thresholds must be between zero and one")
    clusters = policy["clusters"]
    if clusters["maximum_document_count"] < clusters["minimum_document_count"]:
        raise ValueError("Cluster document bounds are invalid")
    coherence = clusters.get("coherence", {})
    if coherence.get("minimum_shared_feature_documents", 0) < 2:
        raise ValueError("Cluster coherence must require a context feature in at least two records")
    if coherence.get("minimum_core_documents", 0) < 2 or coherence.get("minimum_core_sources", 0) < 2:
        raise ValueError("A coherent discovery core must remain cross-source")
    dispositions = set(policy["known_comparison"]["dispositions"])
    required_dispositions = {
        "merge-existing-direction",
        "covered-by-existing-theme",
        "cross-theme-extension",
        "novel",
    }
    if dispositions != required_dispositions:
        raise ValueError("Discovery comparison dispositions do not match the locked contract")
    retained = set(policy["record_generation"]["retain_dispositions"])
    if not retained.issubset(dispositions) or not retained:
        raise ValueError("Active discovery dispositions are invalid")
    known = policy["known_comparison"]
    if known["recurrent_theme_minimum_documents"] < 2:
        raise ValueError("A recurrent discovery theme must appear in at least two records")
    if known["direction_minimum_recurrent_theme_matches"] < 2:
        raise ValueError("Direction matching must require at least two recurrent constituent themes")
    generation = policy["record_generation"]
    if not 0 < generation["minimum_anchor_support_share"] <= 1:
        raise ValueError("Discovery anchor support share must be between zero and one")
    if generation["phrase_candidate"]["minimum_source_family_count"] < 2:
        raise ValueError("Phrase-only Candidates must span at least two source families")


def _normalized_phrase(value: str) -> str:
    return compact_text(value).casefold().replace("-", " ")


def _source_family(document: dict[str, Any], discovery_policy: dict[str, Any]) -> str:
    return discovery_policy["source_families"].get(document["source_type"], document["source_type"])


def _anchor_is_allowed(concept: dict[str, Any], policy: dict[str, Any]) -> bool:
    if concept.get("kind") != "emergent-phrase":
        return True
    phrase = _normalized_phrase(concept.get("label", ""))
    if not phrase or phrase in {_normalized_phrase(value) for value in policy["anchors"]["blocked_phrases"]}:
        return False
    if policy["anchors"].get("exclude_numeric_phrases") and any(character.isdigit() for character in phrase):
        return False
    return True


def _anchor_index(
    catalog: dict[str, Any], policy: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], int]:
    allowed = set(policy["anchors"]["allowed_kinds"])
    documents = catalog.get("documents", [])
    maximum_documents = max(10, int(len(documents) * policy["anchors"]["maximum_document_fraction"]))
    anchors: dict[str, dict[str, Any]] = {}
    filtered_ids: set[str] = set()
    for document in documents:
        for concept in [*document.get("concepts", []), *document.get("entities", [])]:
            if concept.get("kind") not in allowed:
                continue
            if not _anchor_is_allowed(concept, policy):
                filtered_ids.add(concept["id"])
                continue
            anchor = anchors.setdefault(
                concept["id"],
                {
                    "id": concept["id"],
                    "label": concept["label"],
                    "kind": concept["kind"],
                    "document_ids": set(),
                    "source_ids": set(),
                },
            )
            anchor["document_ids"].add(document["evidence_id"])
            anchor["source_ids"].add(document["source_id"])
        if policy["anchors"].get("include_relationships"):
            for relationship in document.get("relationships", []):
                anchor_id = "relation:" + "|".join(
                    [relationship["subject_id"], relationship["predicate"], relationship["object_id"]]
                )
                anchor = anchors.setdefault(
                    anchor_id,
                    {
                        "id": anchor_id,
                        "label": f"{relationship['subject_id']} {relationship['predicate']} {relationship['object_id']}",
                        "kind": "relationship",
                        "document_ids": set(),
                        "source_ids": set(),
                    },
                )
                anchor["document_ids"].add(document["evidence_id"])
                anchor["source_ids"].add(document["source_id"])
    retained = {
        anchor_id: anchor
        for anchor_id, anchor in anchors.items()
        if policy["anchors"]["minimum_document_count"] <= len(anchor["document_ids"]) <= maximum_documents
        and len(anchor["source_ids"]) >= policy["anchors"]["minimum_source_count"]
    }
    return retained, len(filtered_ids)


class _UnionFind:
    def __init__(self, values: Iterable[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _anchor_components(anchors: dict[str, dict[str, Any]], policy: dict[str, Any]) -> list[list[str]]:
    union = _UnionFind(anchors)
    document_anchors: dict[str, list[str]] = defaultdict(list)
    for anchor_id, anchor in anchors.items():
        for document_id in anchor["document_ids"]:
            document_anchors[document_id].append(anchor_id)
    overlaps: Counter[tuple[str, str]] = Counter()
    for anchor_ids in document_anchors.values():
        ordered = sorted(anchor_ids)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                overlaps[(left, right)] += 1
    merging = policy["merging"]
    for (left, right), intersection in overlaps.items():
        if intersection < merging["minimum_shared_documents"]:
            continue
        left_count = len(anchors[left]["document_ids"])
        right_count = len(anchors[right]["document_ids"])
        jaccard = intersection / (left_count + right_count - intersection)
        containment = intersection / min(left_count, right_count)
        if jaccard >= merging["minimum_jaccard"] or containment >= merging["minimum_containment"]:
            union.union(left, right)
    components: dict[str, list[str]] = defaultdict(list)
    for anchor_id in anchors:
        components[union.find(anchor_id)].append(anchor_id)
    return [sorted(component) for component in components.values()]


def _cluster_id(anchor_ids: list[str]) -> str:
    digest = hashlib.sha256("|".join(anchor_ids).encode("utf-8")).hexdigest()[:10]
    readable = slugify(anchor_ids[0].split(":", 1)[-1])[:42] or "pattern"
    return f"discovery:{readable}-{digest}"


def _context_features(
    document: dict[str, Any],
    component_anchor_ids: set[str],
    policy: dict[str, Any],
) -> set[str]:
    allowed_kinds = set(policy["clusters"]["coherence"]["concept_kinds"])
    features = {f"theme:{theme_id}" for theme_id in document.get("theme_ids", [])}
    features.update(f"action:{action['id']}" for action in document.get("actions", []))
    for concept in [*document.get("concepts", []), *document.get("entities", [])]:
        if concept.get("id") not in component_anchor_ids and concept.get("kind") in allowed_kinds:
            features.add(f"concept:{concept['id']}")
    return features


def _coherent_core(
    documents: list[dict[str, Any]],
    component_anchor_ids: set[str],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return the largest cross-source component joined by recurring context features."""
    coherence = policy["clusters"]["coherence"]
    feature_documents: dict[str, set[str]] = defaultdict(set)
    by_id = {document["evidence_id"]: document for document in documents}
    document_features = {}
    for document in documents:
        features = _context_features(document, component_anchor_ids, policy)
        document_features[document["evidence_id"]] = features
        for feature in features:
            feature_documents[feature].add(document["evidence_id"])
    recurrent_features = {
        feature: document_ids
        for feature, document_ids in feature_documents.items()
        if len(document_ids) >= coherence["minimum_shared_feature_documents"]
    }
    adjacency = {document_id: set() for document_id in by_id}
    for document_ids in recurrent_features.values():
        for document_id in document_ids:
            adjacency[document_id].update(document_ids.difference({document_id}))
    components = []
    unseen = set(by_id)
    while unseen:
        seed = min(unseen)
        stack = [seed]
        component = set()
        while stack:
            document_id = stack.pop()
            if document_id in component:
                continue
            component.add(document_id)
            unseen.discard(document_id)
            stack.extend(sorted(adjacency[document_id].difference(component), reverse=True))
        components.append(component)
    eligible = [
        component
        for component in components
        if len(component) >= coherence["minimum_core_documents"]
        and len({by_id[document_id]["source_id"] for document_id in component})
        >= coherence["minimum_core_sources"]
        and any(adjacency[document_id] for document_id in component)
    ]
    if not eligible:
        return [], []
    selected = sorted(
        eligible,
        key=lambda component: (
            -len({by_id[document_id]["source_id"] for document_id in component}),
            -len(component),
            sorted(component),
        ),
    )[0]
    feature_summary = [
        {"id": feature, "document_count": len(document_ids.intersection(selected))}
        for feature, document_ids in recurrent_features.items()
        if len(document_ids.intersection(selected)) >= coherence["minimum_shared_feature_documents"]
    ]
    feature_summary.sort(key=lambda value: (-value["document_count"], value["id"]))
    return [by_id[document_id] for document_id in sorted(selected)], feature_summary[:12]


def _direction_match(
    cluster: dict[str, Any],
    directions: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any] | None:
    cluster_themes = set(cluster["recurrent_theme_ids"])
    anchor_ids = set(cluster["anchor_ids"])
    anchor_phrases = {_normalized_phrase(anchor["label"]) for anchor in cluster["anchors"]}
    matches = []
    for direction in directions:
        direction_themes = set(direction.get("theme_ids", []))
        recurrent_matches = cluster_themes.intersection(direction_themes)
        theme_recall = len(recurrent_matches) / max(1, len(direction_themes))
        explicit_anchor_ids = anchor_ids.intersection(direction.get("match_anchor_ids", set()))
        known_phrases = {
            _normalized_phrase(value)
            for value in direction.get("match_phrases", [])
            if value
        }
        phrase_matches = sorted(
            phrase
            for phrase in anchor_phrases
            if phrase and phrase in known_phrases
        )
        phrase_match = bool(phrase_matches) and policy["known_comparison"].get("direction_anchor_phrase_match")
        theme_match = (
            len(recurrent_matches)
            >= policy["known_comparison"]["direction_minimum_recurrent_theme_matches"]
            and theme_recall >= policy["known_comparison"]["direction_theme_recall_threshold"]
        )
        if explicit_anchor_ids or phrase_match or theme_match:
            if explicit_anchor_ids:
                basis = "explicit-anchor"
            elif phrase_match:
                basis = "disclosed-phrase"
            else:
                basis = "recurrent-theme-recall"
            matches.append(
                {
                    "kind": "early-signal-direction",
                    "id": direction["id"],
                    "title": direction["title"],
                    "theme_recall": round(theme_recall, 3),
                    "matched_theme_ids": sorted(recurrent_matches),
                    "matched_anchor_ids": sorted(explicit_anchor_ids),
                    "matched_anchor_phrases": phrase_matches,
                    "basis": basis,
                }
            )
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda value: (
            -bool(value["matched_anchor_ids"]),
            -bool(value["matched_anchor_phrases"]),
            -value["theme_recall"],
            value["title"],
        ),
    )[0]


def _theme_anchor_match(cluster: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any] | None:
    anchor_phrases = {
        _normalized_phrase(anchor["label"])
        for anchor in cluster["anchors"]
        if anchor["kind"] != "relationship"
    }
    matches = []
    for theme in taxonomy.get("seed_themes", []):
        known_phrases = {
            _normalized_phrase(value)
            for value in [theme.get("name", ""), *theme.get("aliases", [])]
            if value
        }
        phrase_matches = sorted(
            anchor
            for anchor in anchor_phrases
            if len(anchor.split()) >= 2
            and any(f" {anchor} " in f" {known} " or f" {known} " in f" {anchor} " for known in known_phrases)
        )
        if phrase_matches:
            matches.append((max(len(value) for value in phrase_matches), theme, phrase_matches))
    if not matches:
        return None
    _, theme, phrase_matches = sorted(matches, key=lambda value: (-value[0], value[1]["id"]))[0]
    return {
        "kind": "theme",
        "id": theme["id"],
        "title": theme["name"],
        "matched_anchor_phrases": phrase_matches,
        "basis": "anchor-phrase",
    }


def _theme_match(cluster: dict[str, Any], taxonomy: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any] | None:
    if policy["known_comparison"].get("theme_anchor_phrase_match"):
        anchor_match = _theme_anchor_match(cluster, taxonomy)
        if anchor_match:
            anchor_match["document_share"] = round(
                cluster["theme_document_counts"].get(anchor_match["id"], 0)
                / max(1, cluster["metrics"]["evidence_count"]),
                3,
            )
            return anchor_match
    evidence_count = max(1, cluster["metrics"]["evidence_count"])
    definitions = {theme["id"]: theme for theme in taxonomy.get("seed_themes", [])}
    shares = [
        (count / evidence_count, theme_id)
        for theme_id, count in cluster["theme_document_counts"].items()
        if theme_id in definitions
        and count >= policy["known_comparison"]["recurrent_theme_minimum_documents"]
    ]
    if not shares:
        return None
    share, theme_id = sorted(shares, key=lambda value: (-value[0], value[1]))[0]
    if share < policy["known_comparison"]["existing_theme_document_share"]:
        return None
    return {
        "kind": "theme",
        "id": theme_id,
        "title": definitions[theme_id]["name"],
        "document_share": round(share, 3),
        "matched_anchor_phrases": [],
        "basis": "document-share",
    }


def _known_disposition(
    cluster: dict[str, Any],
    taxonomy: dict[str, Any],
    directions: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    direction = _direction_match(cluster, directions, policy)
    if direction:
        return "merge-existing-direction", direction
    theme = _theme_match(cluster, taxonomy, policy)
    if theme:
        return "covered-by-existing-theme", theme
    if len(cluster["recurrent_theme_ids"]) >= policy["known_comparison"]["cross_theme_minimum"]:
        return "cross-theme-extension", None
    return "novel", None


def _build_clusters(
    catalog: dict[str, Any],
    sources: list[dict[str, Any]],
    discovery_policy: dict[str, Any],
    taxonomy: dict[str, Any],
    directions: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], int, int]:
    documents = {document["evidence_id"]: document for document in catalog.get("documents", [])}
    sources_by_id = {source["id"]: source for source in sources}
    changed_ids = set(catalog.get("changed_document_ids", []))
    anchors, filtered_anchor_count = _anchor_index(catalog, policy)
    components = _anchor_components(anchors, policy)
    clusters = []
    overbroad_count = 0
    for component in components:
        document_ids = sorted(set().union(*(anchors[anchor_id]["document_ids"] for anchor_id in component)))
        if len(document_ids) > policy["clusters"]["maximum_document_count"]:
            overbroad_count += 1
            continue
        raw_documents = [documents[document_id] for document_id in document_ids]
        cap_result = cap_candidate_contributions(raw_documents, sources, discovery_policy)
        capped = cap_result["kept"]
        if (
            len(capped) < policy["clusters"]["minimum_document_count"]
            or len({document["source_id"] for document in capped}) < policy["clusters"]["minimum_source_count"]
        ):
            continue
        coherent_core, context_features = _coherent_core(capped, set(component), policy)
        retained = coherent_core or capped
        retained_ids = {document["evidence_id"] for document in retained}
        retained_anchors = []
        for anchor_id in component:
            anchor = anchors[anchor_id]
            support_ids = retained_ids.intersection(anchor["document_ids"])
            if support_ids:
                retained_anchors.append(
                    {
                        "id": anchor_id,
                        "label": anchor["label"],
                        "kind": anchor["kind"],
                        "document_count": len(support_ids),
                        "source_count": len({documents[document_id]["source_id"] for document_id in support_ids}),
                    }
                )
        retained_anchors.sort(key=lambda value: (-value["source_count"], -value["document_count"], value["label"]))
        retained_anchors = retained_anchors[: policy["clusters"]["maximum_anchors_per_cluster"]]
        theme_counts: Counter[str] = Counter(
            theme_id for document in retained for theme_id in document.get("theme_ids", [])
        )
        theme_ids = [
            theme_id for theme_id, _ in sorted(theme_counts.items(), key=lambda value: (-value[1], value[0]))
        ][: policy["clusters"]["maximum_themes_per_cluster"]]
        recurrent_theme_ids = sorted(
            theme_id
            for theme_id, count in theme_counts.items()
            if count >= policy["known_comparison"]["recurrent_theme_minimum_documents"]
        )
        source_ids = sorted({document["source_id"] for document in retained})
        family_ids = sorted({_source_family(document, discovery_policy) for document in retained})
        publisher_counts: Counter[str] = Counter(
            sources_by_id.get(document["source_id"], {}).get("publisher_id") or document["source_id"]
            for document in retained
        )
        technical_families = set(discovery_policy["technical_source_families"])
        metrics = {
            "evidence_count": len(retained),
            "independent_event_count": len(retained),
            "source_count": len(source_ids),
            "source_family_count": len(family_ids),
            "technical_record_count": sum(
                1 for document in retained if _source_family(document, discovery_policy) in technical_families
            ),
            "dominant_publisher_share": round(max(publisher_counts.values()) / len(retained), 3),
            "raw_evidence_count": len(raw_documents),
            "capped_evidence_count": len(capped),
            "changed_evidence_count": len(retained_ids.intersection(changed_ids)),
        }
        anchor_support_share = round(
            max((anchor["document_count"] for anchor in retained_anchors), default=0) / len(retained),
            3,
        )
        anchor_kinds = {anchor["kind"] for anchor in retained_anchors}
        structural_kinds = set(policy["anchors"]["structural_kinds"])
        entity_kinds = set(policy["anchors"]["entity_kinds"])
        has_structural_anchor = bool(anchor_kinds.intersection(structural_kinds))
        phrase_only = bool(anchor_kinds) and anchor_kinds == {"emergent-phrase"}
        entity_only = bool(anchor_kinds) and anchor_kinds.issubset(entity_kinds)
        support_met = anchor_support_share >= policy["record_generation"]["minimum_anchor_support_share"]
        phrase_spark = policy["record_generation"]["phrase_spark"]
        phrase_candidate = policy["record_generation"]["phrase_candidate"]
        has_phrase_anchor = "emergent-phrase" in anchor_kinds
        phrase_spark_met = (
            has_phrase_anchor
            and metrics["source_count"] >= phrase_spark["minimum_source_count"]
            and metrics["technical_record_count"] >= phrase_spark["minimum_technical_record_count"]
        )
        phrase_candidate_met = (
            has_phrase_anchor
            and metrics["source_count"] >= phrase_candidate["minimum_source_count"]
            and metrics["source_family_count"] >= phrase_candidate["minimum_source_family_count"]
            and metrics["technical_record_count"] >= phrase_candidate["minimum_technical_record_count"]
        )
        meaningful_anchor = has_structural_anchor or has_phrase_anchor
        if not policy["record_generation"].get("allow_entity_only") and entity_only:
            meaningful_anchor = False
        quality = {
            "anchor_support_share": anchor_support_share,
            "anchor_support_met": support_met,
            "has_structural_anchor": has_structural_anchor,
            "phrase_only": phrase_only,
            "entity_only": entity_only,
            "recurrent_theme_count": len(recurrent_theme_ids),
            "context_coherence_met": bool(coherent_core),
            "context_features": context_features,
            "context_outlier_count": len(capped) - len(coherent_core) if coherent_core else len(capped),
            "spark_quality_met": bool(coherent_core)
            and support_met
            and meaningful_anchor
            and (has_structural_anchor or phrase_spark_met),
            "candidate_quality_met": support_met
            and bool(coherent_core)
            and meaningful_anchor
            and (has_structural_anchor or phrase_candidate_met),
        }
        cluster = {
            "id": _cluster_id(sorted(anchor["id"] for anchor in retained_anchors)),
            "anchor_ids": [anchor["id"] for anchor in retained_anchors],
            "anchors": retained_anchors,
            "evidence_ids": sorted(retained_ids),
            "source_ids": source_ids,
            "source_family_ids": family_ids,
            "theme_ids": sorted(theme_ids),
            "recurrent_theme_ids": recurrent_theme_ids,
            "theme_document_counts": dict(sorted(theme_counts.items())),
            "first_seen": min(document["published_at"] for document in retained),
            "last_seen": max(document["published_at"] for document in retained),
            "metrics": metrics,
            "quality": quality,
            "source_cap_exclusions": cap_result["excluded"],
            "materially_changed": bool(metrics["changed_evidence_count"]),
        }
        disposition, nearest = _known_disposition(cluster, taxonomy, directions, policy)
        cluster["disposition"] = disposition
        cluster["nearest_known"] = nearest
        clusters.append(cluster)

    clusters.sort(
        key=lambda value: (
            -value["metrics"]["source_family_count"],
            -value["metrics"]["source_count"],
            -value["metrics"]["evidence_count"],
            value["id"],
        )
    )
    deduplicated = []
    for cluster in clusters:
        document_ids = set(cluster["evidence_ids"])
        if any(
            len(document_ids.intersection(existing["evidence_ids"]))
            / len(document_ids.union(existing["evidence_ids"])) >= 0.80
            for existing in deduplicated
        ):
            continue
        deduplicated.append(cluster)
        if len(deduplicated) == policy["clusters"]["maximum_clusters"]:
            break
    return deduplicated, overbroad_count, filtered_anchor_count


def _record_title(cluster: dict[str, Any], policy: dict[str, Any]) -> str:
    labels = [anchor["label"] for anchor in cluster["anchors"][: policy["record_generation"]["title_anchor_count"]]]
    if not labels:
        return "Unresolved cross-source pattern"
    return " + ".join(label[0].upper() + label[1:] for label in labels)


def _discovery_record(
    cluster: dict[str, Any],
    discovery_policy: dict[str, Any],
    clustering_policy: dict[str, Any],
) -> dict[str, Any] | None:
    if not cluster["materially_changed"] or not cluster["quality"]["spark_quality_met"]:
        return None
    novelty_reviewed = False
    state = discovery_entry_state(cluster["metrics"], discovery_policy, novelty_reviewed=novelty_reviewed)
    if not state:
        return None
    if state == "candidate" and not cluster["quality"]["candidate_quality_met"]:
        state = "spark"
    labels = [anchor["label"] for anchor in cluster["anchors"][:3]]
    label_text = ", ".join(labels)
    theme_text = ", ".join(cluster["recurrent_theme_ids"][:3]) or "no recurrent established theme"
    changed = cluster["metrics"]["changed_evidence_count"]
    why_now = (
        f"{changed} retained evidence records are new or materially changed in the current run."
        if changed
        else "No retained evidence changed in the current run; the record is preserved for review continuity."
    )
    nearest = cluster.get("nearest_known")
    if cluster["disposition"] == "cross-theme-extension":
        novelty = (
            f"The cluster crosses {len(cluster['recurrent_theme_ids'])} recurrent existing themes and is not explained by one tracked "
            f"direction. Its nearest known theme is {nearest['title']}." if nearest else
            f"The cluster crosses {len(cluster['recurrent_theme_ids'])} recurrent existing themes without a matching tracked direction."
        )
    else:
        novelty = "No existing theme or tracked direction meets the configured coverage threshold for this cluster."
    record = {
        "id": cluster["id"],
        "cluster_id": cluster["id"],
        "title": _record_title(cluster, clustering_policy),
        "state": state,
        "observed_pattern": (
            f"{label_text} recur across {cluster['metrics']['independent_event_count']} independent records from "
            f"{cluster['metrics']['source_count']} sources and {cluster['metrics']['source_family_count']} source families, "
            f"alongside {theme_text}."
        ),
        "hypothesis": (
            f"The recurring combination of {label_text} may represent a distinct engineering direction rather than "
            "isolated implementations."
        ),
        "why_now": why_now,
        "novelty": novelty,
        "evidence_ids": cluster["evidence_ids"],
        "source_ids": cluster["source_ids"],
        "source_family_ids": cluster["source_family_ids"],
        "theme_ids": cluster["theme_ids"],
        "concepts": labels,
        "alternative_explanations": [
            "The records may share vocabulary because they describe one release cycle or copied framing rather than a durable direction.",
            "The apparent connection may disappear when implementation details and counterexamples are reviewed.",
        ],
        "confirmation_conditions": [
            "Independent source families repeat the pattern in a later weekly cycle.",
            "A technical artifact or production account demonstrates the combined pattern rather than naming it only.",
        ],
        "invalidation_conditions": [
            "The evidence resolves to one syndicated event, publisher, or product campaign.",
            "No independent reinforcement appears before the Spark becomes dormant.",
        ],
        "first_seen": cluster["first_seen"],
        "last_seen": cluster["last_seen"],
        "metrics": {
            key: cluster["metrics"][key]
            for key in (
                "evidence_count",
                "independent_event_count",
                "source_count",
                "source_family_count",
                "technical_record_count",
                "dominant_publisher_share",
            )
        },
        "eligibility": {
            "decision": "eligible",
            "reason_codes": [
                f"{state}-gate-met",
                cluster["disposition"],
                "structural-anchor" if cluster["quality"]["has_structural_anchor"] else "bounded-phrase-anchor",
                "anchor-support-met",
            ],
            "novelty_reviewed": novelty_reviewed,
        },
        "review": {"status": "pending", "action": None, "rationale": "", "target_id": ""},
        "proposed_disposition": cluster["disposition"],
        "nearest_known": nearest,
        "materially_changed": cluster["materially_changed"],
        "quality": cluster["quality"],
    }
    validate_discovery_record(record, discovery_policy)
    return record


def build_discovery_candidates(
    catalog: dict[str, Any],
    sources: list[dict[str, Any]],
    discovery_policy: dict[str, Any],
    taxonomy: dict[str, Any],
    directions: list[dict[str, Any]],
    clustering_policy: dict[str, Any],
) -> dict[str, Any]:
    validate_discovery_policy(discovery_policy)
    validate_clustering_policy(clustering_policy)
    clusters, overbroad_count, filtered_anchor_count = _build_clusters(
        catalog,
        sources,
        discovery_policy,
        taxonomy,
        directions,
        clustering_policy,
    )
    retained = set(clustering_policy["record_generation"]["retain_dispositions"])
    records = []
    for cluster in clusters:
        if cluster["disposition"] not in retained:
            continue
        record = _discovery_record(cluster, discovery_policy, clustering_policy)
        if record:
            records.append(record)
    records.sort(
        key=lambda value: (
            0 if value["state"] == "candidate" else 1,
            -value["metrics"]["source_family_count"],
            -value["metrics"]["source_count"],
            -value["metrics"]["evidence_count"],
            value["title"],
        )
    )
    records = records[: clustering_policy["record_generation"]["maximum_active_records"]]
    merge_suggestion_clusters = sorted(
        (
            cluster
            for cluster in clusters
            if cluster["disposition"] in {"merge-existing-direction", "covered-by-existing-theme"}
        ),
        key=lambda cluster: (
            0 if cluster["disposition"] == "merge-existing-direction" else 1,
            -cluster["metrics"]["source_family_count"],
            -cluster["metrics"]["source_count"],
            -cluster["metrics"]["evidence_count"],
            cluster["id"],
        ),
    )
    merge_suggestions = [
        {
            "cluster_id": cluster["id"],
            "disposition": cluster["disposition"],
            "nearest_known": cluster["nearest_known"],
            "anchor_labels": [anchor["label"] for anchor in cluster["anchors"]],
            "evidence_ids": cluster["evidence_ids"],
            "source_count": cluster["metrics"]["source_count"],
            "source_family_count": cluster["metrics"]["source_family_count"],
            "materially_changed": cluster["materially_changed"],
        }
        for cluster in merge_suggestion_clusters
    ][: clustering_policy["record_generation"]["maximum_merge_suggestions"]]
    state_counts = Counter(record["state"] for record in records)
    disposition_counts = Counter(cluster["disposition"] for cluster in clusters)
    active_dispositions = set(clustering_policy["record_generation"]["retain_dispositions"])
    coherent_cluster_count = sum(cluster["quality"]["context_coherence_met"] for cluster in clusters)
    quality_eligible_cluster_count = sum(cluster["quality"]["spark_quality_met"] for cluster in clusters)
    unexplained_quality_eligible_count = sum(
        cluster["disposition"] in active_dispositions
        and cluster["quality"]["spark_quality_met"]
        and cluster["materially_changed"]
        for cluster in clusters
    )
    generated_at = catalog.get("meta", {}).get("generated_at")
    return {
        "meta": {
            "schema_version": 1,
            "generated_at": generated_at,
            "method": clustering_policy["method"],
            "input_document_count": catalog.get("meta", {}).get("document_count", 0),
            "input_changed_document_count": catalog.get("meta", {}).get("changed_document_count", 0),
            "cluster_count": len(clusters),
            "overbroad_cluster_count": overbroad_count,
            "filtered_anchor_count": filtered_anchor_count,
            "coherent_cluster_count": coherent_cluster_count,
            "quality_eligible_cluster_count": quality_eligible_cluster_count,
            "explained_cluster_count": disposition_counts["merge-existing-direction"]
            + disposition_counts["covered-by-existing-theme"],
            "unexplained_quality_eligible_count": unexplained_quality_eligible_count,
            "active_record_count": len(records),
            "spark_count": state_counts["spark"],
            "candidate_count": state_counts["candidate"],
            "merge_suggestion_count": len(merge_suggestions),
            "disposition_counts": dict(sorted(disposition_counts.items())),
            "interpretation": "Mechanically generated review leads; zero active records is a valid gated result, not a pipeline failure.",
        },
        "records": records,
        "merge_suggestions": merge_suggestions,
        "clusters": clusters,
    }
