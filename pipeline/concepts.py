from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from .discovery import select_eligible_evidence, validate_discovery_policy
from .normalize import compact_text, slugify


TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.+#][a-z0-9]+)*", re.I)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|[\n\r]+")
STOPWORDS = {
    "a", "about", "after", "again", "against", "all", "also", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "between", "both", "but", "by", "can", "could", "did",
    "do", "does", "doing", "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in",
    "into", "is", "it", "its", "itself", "just", "more", "most", "my", "no", "nor", "not", "now", "of",
    "off", "on", "once", "only", "or", "other", "our", "out", "over", "own", "same", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "why", "will", "with", "would", "you", "your",
    "across", "another", "around", "every", "first", "five", "four", "including", "make", "making", "one",
    "three", "today", "two", "use", "used", "uses", "via",
}


def validate_concept_policy(policy: dict[str, Any]) -> None:
    required = {
        "version",
        "method",
        "purpose",
        "phrase_extraction",
        "primitive_concepts",
        "actions",
        "entity_extraction",
        "relationships",
    }
    missing = required.difference(policy)
    if missing:
        raise ValueError(f"Concept extraction policy is missing: {', '.join(sorted(missing))}")
    if policy["version"] != 1 or policy["method"] != "deterministic-lexical-v1":
        raise ValueError("Unsupported concept extraction policy")
    phrase = policy["phrase_extraction"]
    if not 1 <= phrase["minimum_tokens"] <= phrase["maximum_tokens"] <= 5:
        raise ValueError("Concept phrase length bounds are invalid")
    if phrase["minimum_document_frequency"] < 2:
        raise ValueError("Emergent phrases must recur in at least two records")
    if not 0 < phrase["maximum_document_fraction"] < 1:
        raise ValueError("maximum_document_fraction must be between zero and one")
    concept_ids = [concept["id"] for concept in policy["primitive_concepts"]]
    if len(concept_ids) != len(set(concept_ids)):
        raise ValueError("Primitive concept ids must be unique")
    for concept in policy["primitive_concepts"]:
        if not concept.get("label") or not concept.get("aliases"):
            raise ValueError(f"Primitive concept is incomplete: {concept.get('id', '')}")
    if any(not aliases for aliases in policy["actions"].values()):
        raise ValueError("Every controlled action needs at least one lexical form")


def _normalize_text(value: str) -> str:
    value = compact_text(value).casefold().replace("-", " ").replace("/", " ")
    return " ".join(TOKEN_RE.findall(value))


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized = _normalize_text(phrase)
    return bool(normalized) and f" {normalized} " in f" {text} "


def _phrase_position(text: str, phrase: str) -> int:
    normalized = _normalize_text(phrase)
    if not normalized:
        return -1
    position = f" {text} ".find(f" {normalized} ")
    return position - 1 if position >= 0 else -1


def _searchable(item: dict[str, Any]) -> str:
    values = [
        item.get("title", ""),
        item.get("summary", ""),
        *item.get("tags", []),
        *item.get("projects", []),
    ]
    return compact_text(" ".join(str(value) for value in values if value))


def _controlled_lexicon(
    taxonomy: dict[str, Any],
    keywords: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    concepts: list[dict[str, Any]] = []
    for theme in taxonomy.get("seed_themes", []):
        aliases = [theme["name"], *theme.get("aliases", []), *keywords.get("themes", {}).get(theme["id"], [])]
        concepts.append(
            {
                "id": f"theme:{theme['id']}",
                "label": theme["name"],
                "kind": "theme",
                "aliases": sorted(set(aliases), key=lambda value: (-len(value), value)),
            }
        )
    for primitive in policy["primitive_concepts"]:
        concepts.append(
            {
                "id": f"primitive:{primitive['id']}",
                "label": primitive["label"],
                "kind": "primitive",
                "aliases": sorted(set(primitive["aliases"]), key=lambda value: (-len(value), value)),
            }
        )
    return concepts


def _extract_controlled(item: dict[str, Any], lexicon: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = _normalize_text(_searchable(item))
    extracted = []
    for concept in lexicon:
        matches = [alias for alias in concept["aliases"] if _contains_phrase(text, alias)]
        if matches:
            extracted.append(
                {
                    "id": concept["id"],
                    "label": concept["label"],
                    "kind": concept["kind"],
                    "matched_terms": matches[:6],
                }
            )
    return extracted


def _phrase_candidates(text: str, policy: dict[str, Any]) -> Counter[str]:
    config = policy["phrase_extraction"]
    generic = set(config["generic_domain_tokens"])
    blocked = {_normalize_text(value) for value in config["blocked_phrases"]}
    tokens = _normalize_text(text).split()
    candidates: Counter[str] = Counter()
    for size in range(config["minimum_tokens"], config["maximum_tokens"] + 1):
        for index in range(len(tokens) - size + 1):
            phrase_tokens = tokens[index:index + size]
            if any(token in STOPWORDS for token in phrase_tokens):
                continue
            if all(token in generic for token in phrase_tokens):
                continue
            if any(len(token) < 3 and not token.isdigit() for token in phrase_tokens):
                continue
            phrase = " ".join(phrase_tokens)
            if phrase in blocked or all(token.isdigit() for token in phrase_tokens):
                continue
            candidates[phrase] += 1
    return candidates


def _emergent_phrases(
    items: list[dict[str, Any]],
    policy: dict[str, Any],
    controlled_aliases: set[str],
) -> dict[str, list[dict[str, Any]]]:
    config = policy["phrase_extraction"]
    per_document: dict[str, Counter[str]] = {}
    title_phrases: dict[str, set[str]] = {}
    document_frequency: Counter[str] = Counter()
    for item in items:
        candidates = _phrase_candidates(_searchable(item), policy)
        per_document[item["id"]] = candidates
        title_phrases[item["id"]] = set(_phrase_candidates(item.get("title", ""), policy))
        document_frequency.update(candidates.keys())

    document_count = max(1, len(items))
    maximum_frequency = max(
        config["minimum_document_frequency"],
        math.floor(document_count * config["maximum_document_fraction"]),
    )
    output: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        scored = []
        for phrase, term_frequency in per_document[item["id"]].items():
            if phrase in controlled_aliases:
                continue
            frequency = document_frequency[phrase]
            if frequency < config["minimum_document_frequency"] or frequency > maximum_frequency:
                continue
            inverse_frequency = math.log((1 + document_count) / (1 + frequency)) + 1
            length_bonus = 1 + 0.12 * (len(phrase.split()) - config["minimum_tokens"])
            title_bonus = config["title_weight"] if phrase in title_phrases[item["id"]] else 1
            score = (1 + math.log(term_frequency)) * inverse_frequency * length_bonus * title_bonus
            if score >= config["minimum_score"]:
                scored.append((score, phrase, frequency))
        scored.sort(key=lambda value: (-value[0], -len(value[1].split()), value[1]))
        selected: list[tuple[float, str, int]] = []
        for candidate in scored:
            _, phrase, _ = candidate
            if any(f" {phrase} " in f" {existing[1]} " or f" {existing[1]} " in f" {phrase} " for existing in selected):
                continue
            selected.append(candidate)
            if len(selected) == config["maximum_phrases_per_record"]:
                break
        output[item["id"]] = [
            {
                "id": f"phrase:{slugify(phrase)}",
                "label": phrase,
                "kind": "emergent-phrase",
                "matched_terms": [phrase],
                "document_frequency": frequency,
                "score": round(score, 3),
            }
            for score, phrase, frequency in selected
        ]
    return output


def _extract_entities(item: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    config = policy["entity_extraction"]
    blocked = {value.casefold() for value in config["blocked_tags"]}
    entities: dict[str, dict[str, Any]] = {}
    if config.get("include_projects"):
        for project in item.get("projects", []):
            label = compact_text(str(project))
            if label:
                entities[f"project:{slugify(label)}"] = {
                    "id": f"project:{slugify(label)}",
                    "label": label,
                    "kind": "project",
                    "matched_terms": [label],
                }
    if config.get("include_tags"):
        for tag in item.get("tags", []):
            label = compact_text(str(tag))
            if (
                len(label) < config["minimum_tag_length"]
                or label.casefold() in blocked
                or re.fullmatch(r"(?:cs|stat)\.[a-z]+", label, re.I)
            ):
                continue
            entities[f"technology:{slugify(label)}"] = {
                "id": f"technology:{slugify(label)}",
                "label": label,
                "kind": "technology",
                "matched_terms": [label],
            }
    return list(sorted(entities.values(), key=lambda value: (value["kind"], value["label"].casefold())))[: config["maximum_entities_per_record"]]


def _extract_actions(item: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    text = _normalize_text(_searchable(item))
    actions = []
    for action_id, aliases in policy["actions"].items():
        matches = [alias for alias in aliases if _contains_phrase(text, alias)]
        if matches:
            actions.append({"id": action_id, "label": action_id.replace("-", " ").title(), "matched_terms": matches[:6]})
    return actions


def _sentence_relationships(
    item: dict[str, Any],
    concepts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    relationships: dict[tuple[str, str, str], dict[str, Any]] = {}
    maximum = policy["relationships"]["maximum_per_record"]
    nodes = [*concepts, *entities]
    for sentence in SENTENCE_RE.split(_searchable(item)):
        normalized = _normalize_text(sentence)
        if not normalized:
            continue
        present_nodes = []
        for node in nodes:
            positions = [_phrase_position(normalized, term) for term in node.get("matched_terms", [])]
            positions = [position for position in positions if position >= 0]
            if positions:
                present_nodes.append((min(positions), node))
        if len(present_nodes) < 2:
            continue
        present_nodes.sort(key=lambda value: value[0])
        for action in actions:
            action_positions = [_phrase_position(normalized, term) for term in action["matched_terms"]]
            action_positions = [position for position in action_positions if position >= 0]
            if not action_positions:
                continue
            action_position = min(action_positions)
            before = [value for value in present_nodes if value[0] < action_position]
            after = [value for value in present_nodes if value[0] > action_position]
            if before and after:
                subject = before[-1][1]
                target = after[0][1]
            else:
                subject, target = present_nodes[0][1], present_nodes[1][1]
            if subject["id"] == target["id"]:
                continue
            key = (subject["id"], action["id"], target["id"])
            relationships[key] = {
                "subject_id": subject["id"],
                "predicate": action["id"],
                "object_id": target["id"],
                "basis": "same-sentence-co-mention",
            }
            if len(relationships) == maximum:
                return list(relationships.values())
    return list(relationships.values())


def extract_concept_documents(
    items: Iterable[dict[str, Any]],
    taxonomy: dict[str, Any],
    keywords: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    validate_concept_policy(policy)
    rows = list(items)
    lexicon = _controlled_lexicon(taxonomy, keywords, policy)
    controlled_aliases = {
        _normalize_text(alias)
        for concept in lexicon
        for alias in concept["aliases"]
    }
    phrases = _emergent_phrases(rows, policy, controlled_aliases)
    documents = []
    for item in rows:
        controlled = _extract_controlled(item, lexicon)
        entities = _extract_entities(item, policy)
        concepts_by_id = {value["id"]: value for value in [*controlled, *phrases[item["id"]]]}
        concepts = list(sorted(concepts_by_id.values(), key=lambda value: (value["kind"], value["label"].casefold())))
        actions = _extract_actions(item, policy)
        relationships = _sentence_relationships(item, controlled, entities, actions, policy)
        documents.append(
            {
                "evidence_id": item["id"],
                "source_id": item["source_id"],
                "source_type": item["source_type"],
                "published_at": item["published_at"],
                "theme_ids": sorted(item.get("theme_ids", [])),
                "concepts": concepts,
                "entities": entities,
                "actions": actions,
                "relationships": relationships,
            }
        )
    return sorted(documents, key=lambda value: (value["published_at"], value["evidence_id"]))


def _document_signature(document: dict[str, Any]) -> str:
    payload = {
        key: document[key]
        for key in ("theme_ids", "concepts", "entities", "actions", "relationships")
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_concept_catalog(
    items: Iterable[dict[str, Any]],
    sources: Iterable[dict[str, Any]],
    discovery_policy: dict[str, Any],
    taxonomy: dict[str, Any],
    keywords: dict[str, Any],
    concept_policy: dict[str, Any],
    *,
    as_of: datetime,
    previous_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_discovery_policy(discovery_policy)
    validate_concept_policy(concept_policy)
    selection = select_eligible_evidence(
        items,
        sources,
        discovery_policy,
        as_of=as_of,
        previous_fingerprints=None,
    )
    selected_items = [entry["evidence"] for entry in selection["eligible"]]
    documents = extract_concept_documents(selected_items, taxonomy, keywords, concept_policy)
    current_fingerprints = {
        entry["evidence"]["id"]: entry["fingerprint"]
        for entry in selection["eligible"]
    }
    previous_fingerprints = (previous_catalog or {}).get("fingerprints", {})
    previous_documents = {
        document["evidence_id"]: document
        for document in (previous_catalog or {}).get("documents", [])
    }
    changed_ids = []
    for document in documents:
        evidence_id = document["evidence_id"]
        prior = previous_documents.get(evidence_id)
        if (
            previous_fingerprints.get(evidence_id) != current_fingerprints[evidence_id]
            or not prior
            or _document_signature(prior) != _document_signature(document)
        ):
            changed_ids.append(evidence_id)
    removed_ids = sorted(set(previous_documents).difference(document["evidence_id"] for document in documents))

    concept_documents: dict[str, set[str]] = defaultdict(set)
    concept_sources: dict[str, set[str]] = defaultdict(set)
    concept_labels: dict[str, tuple[str, str]] = {}
    relationship_counts: Counter[tuple[str, str, str]] = Counter()
    for document in documents:
        for concept in [*document["concepts"], *document["entities"]]:
            concept_documents[concept["id"]].add(document["evidence_id"])
            concept_sources[concept["id"]].add(document["source_id"])
            concept_labels[concept["id"]] = (concept["label"], concept["kind"])
        relationship_counts.update(
            (relationship["subject_id"], relationship["predicate"], relationship["object_id"])
            for relationship in document["relationships"]
        )
    concept_index = [
        {
            "id": concept_id,
            "label": concept_labels[concept_id][0],
            "kind": concept_labels[concept_id][1],
            "document_count": len(document_ids),
            "source_count": len(concept_sources[concept_id]),
        }
        for concept_id, document_ids in concept_documents.items()
    ]
    concept_index.sort(key=lambda value: (-value["source_count"], -value["document_count"], value["label"].casefold()))
    relationship_index = [
        {
            "subject_id": subject,
            "predicate": predicate,
            "object_id": target,
            "document_count": count,
        }
        for (subject, predicate, target), count in relationship_counts.items()
    ]
    relationship_index.sort(key=lambda value: (-value["document_count"], value["subject_id"], value["predicate"], value["object_id"]))

    return {
        "meta": {
            "schema_version": 1,
            "generated_at": as_of.astimezone(timezone.utc).isoformat(),
            "method": concept_policy["method"],
            "window_days": discovery_policy["eligibility"]["lookback_days"],
            "document_count": len(documents),
            "changed_document_count": len(changed_ids),
            "removed_document_count": len(removed_ids),
            "excluded_record_count": len(selection["excluded"]),
            "interpretation": "Lexical observations for clustering; not themes, trends, or findings.",
        },
        "changed_document_ids": sorted(changed_ids),
        "removed_document_ids": removed_ids,
        "fingerprints": dict(sorted(current_fingerprints.items())),
        "concept_index": concept_index,
        "relationship_index": relationship_index,
        "documents": documents,
    }
