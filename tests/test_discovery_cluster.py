import unittest
from pathlib import Path

import yaml

from pipeline.discovery import validate_discovery_record
from pipeline.discovery_cluster import build_discovery_candidates, validate_clustering_policy
from pipeline.export_public import validate_public_payload
from pipeline.research import EARLY_SIGNAL_DIRECTIONS


ROOT = Path(__file__).resolve().parents[1]


class DiscoveryClusteringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery_policy = yaml.safe_load((ROOT / "config/discovery.yml").read_text(encoding="utf-8"))
        cls.clustering_policy = yaml.safe_load((ROOT / "config/discovery-clustering.yml").read_text(encoding="utf-8"))
        cls.taxonomy = yaml.safe_load((ROOT / "config/taxonomy.yml").read_text(encoding="utf-8"))
        cls.sources = [
            {"id": "paper", "channel": "paper", "enabled": True, "publisher_id": "paper-publisher"},
            {"id": "repo", "channel": "repository", "enabled": True, "publisher_id": "repo-publisher"},
            {"id": "builder", "channel": "first-party-lab", "enabled": True, "publisher_id": "builder-publisher"},
            {"id": "expert", "channel": "expert-newsletter", "enabled": True, "publisher_id": "expert-publisher"},
            {"id": "paper-two", "channel": "paper", "enabled": True, "publisher_id": "paper-two-publisher"},
        ]
        cls.catalog = {
            "meta": {"generated_at": "2026-09-23T12:00:00+00:00", "document_count": 12, "changed_document_count": 12},
            "changed_document_ids": [f"evidence:{index}" for index in range(1, 13)],
            "documents": [
                cls.document(1, "paper", "paper", "phrase:policy-firewall", "policy firewall", ["voice-audio"]),
                cls.document(2, "repo", "repository", "phrase:policy-firewall", "policy firewall", ["ai-native-gtm"]),
                cls.document(3, "builder", "first-party-lab", "phrase:policy-firewall", "policy firewall", ["specialized-inference-silicon"]),
                cls.document(4, "paper", "paper", "phrase:context-escrow", "context escrow", ["memory-context"]),
                cls.document(5, "repo", "repository", "phrase:context-escrow", "context escrow", ["document-knowledge-systems"]),
                cls.document(6, "paper-two", "paper", "phrase:context-escrow", "context escrow", ["operational-ontology"]),
                cls.document(7, "paper", "paper", "primitive:data-sovereignty", "Data sovereignty", ["open-local-inference"]),
                cls.document(8, "repo", "repository", "primitive:data-sovereignty", "Data sovereignty", ["assurance-infrastructure"]),
                cls.document(9, "builder", "first-party-lab", "primitive:data-sovereignty", "Data sovereignty", ["enterprise-vertical-ai"]),
                cls.document(10, "paper", "paper", "technology:swe-bench", "SWE-bench", ["coding-agents"]),
                cls.document(11, "repo", "repository", "technology:swe-bench", "SWE-bench", ["coding-agents"]),
                cls.document(12, "expert", "expert-newsletter", "technology:swe-bench", "SWE-bench", ["coding-agents"]),
            ],
        }

    @staticmethod
    def document(index, source_id, source_type, concept_id, label, theme_ids):
        return {
            "evidence_id": f"evidence:{index}",
            "source_id": source_id,
            "source_type": source_type,
            "published_at": f"2026-09-{10 + index:02d}",
            "theme_ids": theme_ids,
            "concepts": [
                {
                    "id": concept_id,
                    "label": label,
                    "kind": concept_id.split(":", 1)[0] if concept_id.startswith("primitive:") else "emergent-phrase",
                    "matched_terms": [label],
                }
            ],
            "entities": (
                [{"id": concept_id, "label": label, "kind": "technology", "matched_terms": [label]}]
                if concept_id.startswith("technology:") else []
            ),
            "actions": [{"id": "evaluate", "label": "Evaluate", "matched_terms": ["evaluate"]}],
            "relationships": [],
        }

    def test_policy_locks_cross_source_anchor_and_comparison_rules(self):
        validate_clustering_policy(self.clustering_policy)
        self.assertEqual(self.clustering_policy["anchors"]["minimum_source_count"], 2)
        self.assertEqual(
            set(self.clustering_policy["record_generation"]["retain_dispositions"]),
            {"cross-theme-extension", "novel"},
        )

    def test_classifies_novel_patterns_and_routes_known_patterns_to_merge(self):
        result = build_discovery_candidates(
            self.catalog,
            self.sources,
            self.discovery_policy,
            self.taxonomy,
            EARLY_SIGNAL_DIRECTIONS,
            self.clustering_policy,
        )
        records = {record["title"].casefold(): record for record in result["records"]}
        self.assertIn("policy firewall", records)
        self.assertEqual(records["policy firewall"]["state"], "candidate")
        self.assertIn("context escrow", records)
        self.assertEqual(records["context escrow"]["state"], "spark")
        suggestions = result["merge_suggestions"]
        sovereignty = next(item for item in suggestions if "Data sovereignty" in item["anchor_labels"])
        self.assertEqual(sovereignty["disposition"], "merge-existing-direction")
        self.assertEqual(sovereignty["nearest_known"]["id"], "enterprise-data-boundary")
        swe_bench = next(item for item in suggestions if "SWE-bench" in item["anchor_labels"])
        self.assertEqual(swe_bench["disposition"], "covered-by-existing-theme")
        self.assertEqual(swe_bench["nearest_known"]["id"], "coding-agents")

    def test_generated_records_satisfy_the_formal_contract(self):
        result = build_discovery_candidates(
            self.catalog,
            self.sources,
            self.discovery_policy,
            self.taxonomy,
            EARLY_SIGNAL_DIRECTIONS,
            self.clustering_policy,
        )
        for record in result["records"]:
            validate_discovery_record(record, self.discovery_policy)
        validate_public_payload(result)
        self.assertEqual(result["meta"]["candidate_count"], 1)
        self.assertEqual(result["meta"]["spark_count"], 1)

    def test_filters_generic_release_phrases_and_requires_context_coherence(self):
        documents = [
            self.document(1, "paper", "paper", "phrase:high-level", "high level", ["voice-audio"]),
            self.document(2, "repo", "repository", "phrase:high-level", "high level", ["ai-native-gtm"]),
            self.document(3, "builder", "first-party-lab", "phrase:high-level", "high level", ["memory-context"]),
            self.document(4, "paper", "paper", "phrase:gpt-6-astra", "GPT 6 Astra", ["small-specialized-models"]),
            self.document(5, "repo", "repository", "phrase:gpt-6-astra", "GPT 6 Astra", ["coding-agents"]),
            self.document(6, "builder", "first-party-lab", "phrase:gpt-6-astra", "GPT 6 Astra", ["agent-harnesses"]),
            self.document(7, "paper", "paper", "primitive:human-intervention", "Human intervention", ["robotics-embodied-ai"]),
            self.document(8, "repo", "repository", "primitive:human-intervention", "Human intervention", ["assurance-infrastructure"]),
            self.document(9, "builder", "first-party-lab", "primitive:human-intervention", "Human intervention", ["enterprise-vertical-ai"]),
        ]
        for document, action in zip(documents[-3:], ("train", "deploy", "secure")):
            document["actions"] = [{"id": action, "label": action.title(), "matched_terms": [action]}]
        catalog = {
            "meta": {"generated_at": "2026-09-23T12:00:00+00:00", "document_count": 9, "changed_document_count": 9},
            "changed_document_ids": [document["evidence_id"] for document in documents],
            "documents": documents,
        }
        result = build_discovery_candidates(
            catalog,
            self.sources,
            self.discovery_policy,
            self.taxonomy,
            EARLY_SIGNAL_DIRECTIONS,
            self.clustering_policy,
        )
        labels = {anchor["label"].casefold() for cluster in result["clusters"] for anchor in cluster["anchors"]}
        self.assertNotIn("high level", labels)
        self.assertNotIn("gpt 6 astra", labels)
        human = next(cluster for cluster in result["clusters"] if "Human intervention" in [a["label"] for a in cluster["anchors"]])
        self.assertFalse(human["quality"]["context_coherence_met"])
        self.assertEqual(result["records"], [])


if __name__ == "__main__":
    unittest.main()
