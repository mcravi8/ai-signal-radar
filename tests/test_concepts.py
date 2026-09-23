import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.concepts import build_concept_catalog, extract_concept_documents, validate_concept_policy
from pipeline.export_public import validate_public_payload


ROOT = Path(__file__).resolve().parents[1]


class ConceptExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery_policy = yaml.safe_load((ROOT / "config/discovery.yml").read_text(encoding="utf-8"))
        cls.concept_policy = yaml.safe_load((ROOT / "config/discovery-concepts.yml").read_text(encoding="utf-8"))
        cls.taxonomy = yaml.safe_load((ROOT / "config/taxonomy.yml").read_text(encoding="utf-8"))
        cls.keywords = yaml.safe_load((ROOT / "config/keywords.yml").read_text(encoding="utf-8"))
        cls.sources = [
            {
                "id": "paper-source",
                "channel": "paper",
                "enabled": True,
                "publisher_id": "research-org",
            },
            {
                "id": "repo-source",
                "channel": "repository",
                "enabled": True,
                "publisher_id": "engineering-org",
            },
            {
                "id": "builder-source",
                "channel": "first-party-lab",
                "enabled": True,
                "publisher_id": "builder-org",
            },
        ]
        cls.items = [
            {
                "id": "paper:one",
                "source_id": "paper-source",
                "source_type": "paper",
                "title": "Governed inference routing for confidential data",
                "summary": "A model router routes private data through a governed context boundary and policy firewall.",
                "url": "https://example.com/paper-one",
                "published_at": "2026-09-22",
                "tags": ["confidential computing"],
                "projects": ["BoundaryKit"],
                "theme_ids": ["model-routing", "assurance-infrastructure"],
            },
            {
                "id": "repo:two",
                "source_id": "repo-source",
                "source_type": "repository",
                "title": "Governed inference routing for private execution",
                "summary": "The agent runtime routes requests while a policy firewall protects confidential data.",
                "url": "https://example.com/repo-two",
                "published_at": "2026-09-21",
                "tags": ["tenant isolation"],
                "projects": ["PrivateRuntime"],
                "theme_ids": ["agent-harnesses", "model-routing"],
            },
            {
                "id": "builder:three",
                "source_id": "builder-source",
                "source_type": "first-party-lab",
                "title": "Data sovereignty through governed inference routing",
                "summary": "An on-prem deployment protects proprietary data and monitors model serving.",
                "url": "https://example.com/builder-three",
                "published_at": "2026-09-20",
                "tags": ["data sovereignty"],
                "projects": ["SovereignStack"],
                "theme_ids": ["open-local-inference", "assurance-infrastructure"],
            },
        ]

    def test_policy_is_bounded_and_model_free(self):
        validate_concept_policy(self.concept_policy)
        self.assertEqual(self.concept_policy["method"], "deterministic-lexical-v1")
        self.assertGreaterEqual(self.concept_policy["phrase_extraction"]["minimum_document_frequency"], 2)

    def test_extracts_controlled_dynamic_and_entity_concepts(self):
        documents = extract_concept_documents(
            self.items,
            self.taxonomy,
            self.keywords,
            self.concept_policy,
        )
        paper = next(document for document in documents if document["evidence_id"] == "paper:one")
        concept_ids = {concept["id"] for concept in paper["concepts"]}
        entity_ids = {entity["id"] for entity in paper["entities"]}
        action_ids = {action["id"] for action in paper["actions"]}
        self.assertIn("theme:model-routing", concept_ids)
        self.assertIn("primitive:proprietary-data-boundary", concept_ids)
        self.assertIn("phrase:policy-firewall", concept_ids)
        self.assertIn("project:boundarykit", entity_ids)
        self.assertIn("technology:confidential-computing", entity_ids)
        self.assertIn("route", action_ids)
        self.assertIn("govern", action_ids)

    def test_relationships_are_bounded_co_mentions_without_source_excerpt(self):
        documents = extract_concept_documents(
            self.items,
            self.taxonomy,
            self.keywords,
            self.concept_policy,
        )
        relationships = [relationship for document in documents for relationship in document["relationships"]]
        self.assertTrue(relationships)
        self.assertTrue(all(relationship["basis"] == "same-sentence-co-mention" for relationship in relationships))
        serialized = json.dumps(documents)
        self.assertNotIn("excerpt", serialized)
        self.assertNotIn("summary", serialized)
        self.assertNotIn("title", serialized)

    def test_catalog_marks_only_materially_changed_documents_after_first_run(self):
        first = build_concept_catalog(
            self.items,
            self.sources,
            self.discovery_policy,
            self.taxonomy,
            self.keywords,
            self.concept_policy,
            as_of=datetime(2026, 9, 23, tzinfo=timezone.utc),
        )
        self.assertEqual(first["meta"]["document_count"], 3)
        self.assertEqual(first["meta"]["changed_document_count"], 3)
        second = build_concept_catalog(
            self.items,
            self.sources,
            self.discovery_policy,
            self.taxonomy,
            self.keywords,
            self.concept_policy,
            as_of=datetime(2026, 9, 24, tzinfo=timezone.utc),
            previous_catalog=first,
        )
        self.assertEqual(second["meta"]["changed_document_count"], 0)
        changed = json.loads(json.dumps(self.items))
        changed[0]["summary"] += " A release gate evaluates every routed request."
        third = build_concept_catalog(
            changed,
            self.sources,
            self.discovery_policy,
            self.taxonomy,
            self.keywords,
            self.concept_policy,
            as_of=datetime(2026, 9, 24, tzinfo=timezone.utc),
            previous_catalog=second,
        )
        self.assertIn("paper:one", third["changed_document_ids"])
        validate_public_payload(third)


if __name__ == "__main__":
    unittest.main()
