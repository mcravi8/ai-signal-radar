import copy
import json
import unittest
from pathlib import Path

import yaml

from pipeline.weekly_review import _material_changes, _review_headline, build_weekly_review


ROOT = Path(__file__).resolve().parents[1]


class WeeklyReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.research = json.loads((ROOT / "data/public/research.json").read_text())
        cls.operating = json.loads((ROOT / "data/public/operating-model.json").read_text())
        cls.config = yaml.safe_load((ROOT / "config/weekly-review.yml").read_text())

    def test_candidate_pool_is_bounded_and_cross_source(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        self.assertEqual(review["meta"]["candidate_pool_count"], 36)
        self.assertLessEqual(len(review["assessment_queue"]), 10)
        self.assertTrue(all(item["materially_changed"] for item in review["assessment_queue"]))
        self.assertTrue(any(item["linked_requirement"] for item in review["assessment_queue"]))

    def test_priority_never_changes_requirement_maturity(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        maturity = {item["id"]: item["maturity"] for item in self.operating["requirements"]}
        self.assertEqual(maturity, {item["id"]: item["maturity"] for item in self.operating["requirements"]})
        self.assertIn("cannot create, promote, or demote", review["summary"]["interpretation"])

    def test_second_identical_cycle_preserves_the_published_review(self):
        first = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        second = build_weekly_review(self.research, self.operating, self.operating, first, self.config)
        self.assertEqual(second["assessment_queue"], first["assessment_queue"])
        self.assertTrue(second["meta"]["idempotent_regeneration"])

    def test_unresolved_queue_item_survives_an_unrelated_same_cycle_update(self):
        first = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        self.assertTrue(first["assessment_queue"])
        prior_id = first["assessment_queue"][0]["id"]
        previous_operating = json.loads(json.dumps(self.operating))
        previous_operating["requirements"][0]["evidence"] = []
        second = build_weekly_review(self.research, self.operating, previous_operating, first, self.config)
        self.assertIn(prior_id, {item["id"] for item in second["assessment_queue"]})

    def test_same_cycle_adjudication_removes_item_from_preserved_queue(self):
        base_config = copy.deepcopy(self.config)
        base_config["candidate_adjudications"] = []
        first = build_weekly_review(self.research, self.operating, self.operating, None, base_config)
        target = first["assessment_queue"][0]
        reviewed_config = copy.deepcopy(base_config)
        reviewed_config["candidate_adjudications"] = [{
            "candidate_id": target["id"],
            "reviewed_at": first["meta"]["as_of"],
            "outcome": "reviewed-for-test",
            "requirement_ids": [],
            "decision": "Reviewed.",
            "rationale": "Test-only adjudication record.",
            "reviewed_state": {
                "stage": target.get("stage"),
                "movement": target.get("movement"),
                "evidence_count": target["metrics"]["evidence_count"],
                "source_count": target["metrics"]["source_count"],
            },
        }]
        second = build_weekly_review(
            self.research,
            self.operating,
            self.operating,
            first,
            reviewed_config,
        )
        self.assertNotIn(target["id"], {item["id"] for item in second["assessment_queue"]})
        self.assertEqual(second["meta"]["assessment_queue_count"], len(second["assessment_queue"]))

    def test_verification_families_state_their_boundary(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        self.assertEqual(len(review["verification_families"]), 6)
        self.assertTrue(all("Supporting verification" in item["boundary"] for item in review["verification_families"]))

    def test_review_headline_uses_singular_candidate_grammar(self):
        self.assertEqual(
            _review_headline(4, 1, 35),
            "4 candidate decisions are recorded; 1 candidate remains in the bounded assessment queue.",
        )

    def test_momentum_decay_and_priority_shift_do_not_reopen_a_review(self):
        previous = {
            "stage": "broadly-corroborated",
            "movement": "rising",
            "metrics": {"evidence_count": 20, "source_count": 8, "recent_evidence_count": 6},
            "priority": {"total": 90},
        }
        candidate = {
            "stage": "broadly-corroborated",
            "movement": "steady",
            "metrics": {"evidence_count": 20, "source_count": 8, "recent_evidence_count": 5},
            "priority": {"total": 72},
        }
        self.assertEqual(
            _material_changes(candidate, previous, self.config["material_change_thresholds"]),
            [],
        )

    def test_reviewed_candidates_have_explicit_adjudications(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        adjudications = {item["candidate_id"]: item for item in review["adjudications"]}
        self.assertEqual(
            set(adjudications),
            {
                "theme:robotics-embodied-ai",
                "theme:agent-harnesses",
                "theme:coding-agents",
                "theme:frontier-inference-infrastructure",
                "theme:skills-integrations",
                "early:modular-agent-stack",
                "early:enterprise-data-boundary",
                "theme:voice-audio",
                "theme:open-local-inference",
                "theme:multimodal-3d",
                "theme:training-self-improvement",
                "expert-finding:evaluation-as-system-design",
            },
        )
        self.assertEqual(adjudications["theme:robotics-embodied-ai"]["outcome"], "conditional-requirement-added")
        self.assertEqual(
            adjudications["early:enterprise-data-boundary"]["outcome"],
            "conditional-requirement-added",
        )
        self.assertEqual(
            adjudications["theme:voice-audio"]["outcome"],
            "modality-signal-not-general-requirement",
        )
        self.assertEqual(
            adjudications["theme:training-self-improvement"]["requirement_ids"],
            ["evaluation-release-gates"],
        )
        self.assertTrue(all(item["status"] in {"current", "revisit-required"} for item in adjudications.values()))
        audited = [item for item in adjudications.values() if item.get("evidence_review")]
        self.assertTrue(all(item["evidence_review"]["status"] == "complete" for item in audited))
        queued_ids = {item["id"] for item in review["assessment_queue"]}
        current_ids = {
            candidate_id for candidate_id, item in adjudications.items()
            if item["status"] == "current"
        }
        self.assertFalse(current_ids.intersection(queued_ids))
        revisit_ids = {
            candidate_id for candidate_id, item in adjudications.items()
            if item["status"] == "revisit-required"
        }
        queued_adjudication_ids = queued_ids.intersection(adjudications)
        self.assertTrue(queued_adjudication_ids)
        self.assertTrue(queued_adjudication_ids.issubset(revisit_ids))


if __name__ == "__main__":
    unittest.main()
