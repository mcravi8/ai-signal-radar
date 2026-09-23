import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.discovery import (
    cap_candidate_contributions,
    discovery_entry_state,
    evidence_fingerprint,
    select_eligible_evidence,
    validate_discovery_policy,
    validate_discovery_record,
)


ROOT = Path(__file__).resolve().parents[1]


class DiscoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = yaml.safe_load((ROOT / "config/discovery.yml").read_text(encoding="utf-8"))
        cls.sources = [
            {
                "id": "primary-paper",
                "channel": "paper",
                "enabled": True,
                "publisher_id": "research-org",
            },
            {
                "id": "paper-roundup",
                "channel": "paper-curation",
                "enabled": True,
                "publisher_id": "roundup-org",
            },
            {
                "id": "engineering-feed",
                "channel": "repository",
                "enabled": True,
                "publisher_id": "engineering-org",
            },
            {
                "id": "second-engineering-feed",
                "channel": "repository",
                "enabled": True,
                "publisher_id": "engineering-org",
            },
        ]

    def item(self, item_id, source_id, title, published_at="2026-09-22", **extra):
        return {
            "id": item_id,
            "source_id": source_id,
            "source_type": next(source["channel"] for source in self.sources if source["id"] == source_id),
            "title": title,
            "summary": extra.pop("summary", "A bounded public technical description."),
            "url": extra.pop("url", f"https://example.com/{item_id}"),
            "published_at": published_at,
            "tags": extra.pop("tags", []),
            "projects": extra.pop("projects", []),
            "theme_ids": extra.pop("theme_ids", []),
            **extra,
        }

    def test_policy_locks_record_states_and_candidate_gate(self):
        validate_discovery_policy(self.policy)
        self.assertEqual(
            set(self.policy["states"]),
            {"spark", "candidate", "approved", "merged", "rejected", "dormant"},
        )
        gate = self.policy["state_entry_gates"]["candidate"]
        self.assertEqual(gate["minimum_source_count"], 3)
        self.assertEqual(gate["minimum_source_family_count"], 2)
        self.assertEqual(gate["maximum_dominant_publisher_share"], 0.5)

    def test_record_separates_observation_from_inference(self):
        record = {
            "id": "candidate:governed-data-boundary",
            "title": "Governed enterprise data boundaries",
            "state": "candidate",
            "observed_pattern": "Several independent records describe controlled access to private data.",
            "hypothesis": "Enterprise data will remain behind a replaceable model boundary.",
            "why_now": "Three new records appeared in the current discovery window.",
            "novelty": "The pattern connects privacy, inference, and operational context themes.",
            "evidence_ids": ["a", "b", "c"],
            "source_ids": ["primary-paper", "engineering-feed", "paper-roundup"],
            "source_family_ids": ["research", "engineering"],
            "theme_ids": ["open-local-inference", "operational-ontology"],
            "concepts": ["data sovereignty", "governed inference"],
            "alternative_explanations": ["The language may reflect vendor positioning rather than adoption."],
            "confirmation_conditions": ["Independent production architectures disclose the boundary."],
            "invalidation_conditions": ["Customers routinely permit provider training on proprietary data."],
            "first_seen": "2026-09-10",
            "last_seen": "2026-09-22",
            "metrics": {
                "evidence_count": 3,
                "independent_event_count": 3,
                "source_count": 3,
                "source_family_count": 2,
                "technical_record_count": 2,
                "dominant_publisher_share": 1 / 3,
            },
            "eligibility": {"decision": "eligible", "reason_codes": ["candidate-gate-met"]},
            "review": {"status": "pending", "action": None, "rationale": "", "target_id": ""},
        }
        validate_discovery_record(record, self.policy)
        observations = set(self.policy["record_contract"]["observation_fields"])
        inferences = set(self.policy["record_contract"]["inference_fields"])
        self.assertFalse(observations.intersection(inferences))

    def test_terminal_state_requires_matching_human_decision(self):
        record = {
            "id": "candidate:test",
            "title": "Test pattern",
            "state": "approved",
            "observed_pattern": "Observed public records agree.",
            "hypothesis": "A bounded hypothesis.",
            "why_now": "New evidence arrived.",
            "novelty": "It is not represented by an existing direction.",
            "evidence_ids": ["a", "b", "c"],
            "source_ids": ["primary-paper", "paper-roundup", "engineering-feed"],
            "source_family_ids": ["research", "engineering"],
            "theme_ids": [],
            "concepts": ["test"],
            "alternative_explanations": ["It may be noise."],
            "confirmation_conditions": ["Another source confirms it."],
            "invalidation_conditions": ["The implementation fails."],
            "first_seen": "2026-09-20",
            "last_seen": "2026-09-22",
            "metrics": {
                "evidence_count": 3,
                "independent_event_count": 3,
                "source_count": 3,
                "source_family_count": 2,
                "technical_record_count": 2,
                "dominant_publisher_share": 1 / 3,
            },
            "eligibility": {"decision": "eligible", "reason_codes": []},
            "review": {"status": "pending", "action": None, "rationale": "", "target_id": ""},
        }
        with self.assertRaisesRegex(ValueError, "requires review action track"):
            validate_discovery_record(record, self.policy)
        record["review"] = {
            "status": "decided",
            "action": "track",
            "rationale": "The evidence boundary is coherent.",
            "target_id": "early-signal:test-pattern",
        }
        validate_discovery_record(record, self.policy)

    def test_entry_state_never_promotes_without_candidate_breadth(self):
        one_technical_record = {
            "evidence_count": 1,
            "independent_event_count": 1,
            "source_count": 1,
            "source_family_count": 1,
            "technical_record_count": 1,
            "dominant_publisher_share": 1.0,
        }
        self.assertIsNone(discovery_entry_state(one_technical_record, self.policy))
        self.assertEqual(
            discovery_entry_state(one_technical_record, self.policy, novelty_reviewed=True),
            "spark",
        )
        candidate_metrics = {
            "evidence_count": 3,
            "independent_event_count": 3,
            "source_count": 3,
            "source_family_count": 2,
            "technical_record_count": 1,
            "dominant_publisher_share": 1 / 3,
        }
        self.assertEqual(discovery_entry_state(candidate_metrics, self.policy), "candidate")

    def test_eligibility_selects_only_recent_new_or_changed_public_records(self):
        paper = self.item("paper", "primary-paper", "A new architecture")
        roundup = self.item(
            "roundup",
            "paper-roundup",
            "A new architecture",
            url="https://roundup.example/a-new-architecture",
        )
        unchanged = self.item("unchanged", "engineering-feed", "An unchanged repository")
        changed = self.item("changed", "engineering-feed", "A materially changed repository")
        stale = self.item("stale", "primary-paper", "An old paper", published_at="2026-07-01")
        unsafe = self.item("unsafe", "primary-paper", "Unsafe record", raw_body="private newsletter body")
        future = self.item("future", "primary-paper", "Future record", published_at="2026-09-30")
        previous = {
            "unchanged": evidence_fingerprint(unchanged, self.policy),
            "changed": "prior-fingerprint",
        }

        result = select_eligible_evidence(
            [paper, roundup, unchanged, changed, stale, unsafe, future],
            self.sources,
            self.policy,
            as_of=datetime(2026, 9, 23, tzinfo=timezone.utc),
            previous_fingerprints=previous,
        )

        selected = {entry["evidence"]["id"]: entry["change_type"] for entry in result["eligible"]}
        self.assertEqual(selected, {"paper": "new-record", "changed": "materially-changed"})
        reasons = {entry["evidence_id"]: entry["reason_codes"] for entry in result["excluded"]}
        self.assertEqual(reasons["roundup"], ["duplicate-event"])
        self.assertEqual(reasons["unchanged"], ["unchanged"])
        self.assertEqual(reasons["stale"], ["outside-window"])
        self.assertEqual(reasons["unsafe"], ["not-public-safe"])
        self.assertEqual(reasons["future"], ["future-dated"])

    def test_candidate_caps_prevent_one_source_or_publisher_from_dominating(self):
        items = [
            self.item("repo-1", "engineering-feed", "Repository one"),
            self.item("repo-2", "engineering-feed", "Repository two", published_at="2026-09-21"),
            self.item("repo-3", "engineering-feed", "Repository three", published_at="2026-09-20"),
            self.item("repo-4", "second-engineering-feed", "Repository four", published_at="2026-09-19"),
            self.item("paper-1", "primary-paper", "Paper one"),
        ]
        result = cap_candidate_contributions(items, self.sources, self.policy)
        self.assertEqual({item["id"] for item in result["kept"]}, {"repo-1", "repo-2", "paper-1"})
        reasons = {entry["evidence_id"]: entry["reason_codes"] for entry in result["excluded"]}
        self.assertIn("source-cap", reasons["repo-3"])
        self.assertEqual(reasons["repo-4"], ["publisher-cap"])

    def test_invalid_policy_cannot_add_an_unreviewed_terminal_state(self):
        invalid = copy.deepcopy(self.policy)
        invalid["states"]["approved"]["terminal"] = True
        invalid["state_transitions"]["approved"] = ["candidate"]
        with self.assertRaisesRegex(ValueError, "Terminal discovery state"):
            validate_discovery_policy(invalid)


if __name__ == "__main__":
    unittest.main()
