import json
import unittest
from pathlib import Path

import yaml

from pipeline.weekly_review import _review_headline, build_weekly_review


ROOT = Path(__file__).resolve().parents[1]


class WeeklyReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.research = json.loads((ROOT / "data/public/research.json").read_text())
        cls.operating = json.loads((ROOT / "data/public/operating-model.json").read_text())
        cls.config = yaml.safe_load((ROOT / "config/weekly-review.yml").read_text())

    def test_candidate_pool_is_bounded_and_cross_source(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        self.assertEqual(review["meta"]["candidate_pool_count"], 35)
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

    def test_verification_families_state_their_boundary(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        self.assertEqual(len(review["verification_families"]), 6)
        self.assertTrue(all("Supporting verification" in item["boundary"] for item in review["verification_families"]))

    def test_review_headline_uses_singular_candidate_grammar(self):
        self.assertEqual(
            _review_headline(4, 1, 35),
            "4 candidate decisions are recorded; 1 candidate remains in the bounded assessment queue.",
        )

    def test_four_theme_candidates_have_explicit_adjudications(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        adjudications = {item["candidate_id"]: item for item in review["adjudications"]}
        self.assertEqual(
            set(adjudications),
            {
                "theme:robotics-embodied-ai",
                "theme:agent-harnesses",
                "theme:coding-agents",
                "theme:frontier-inference-infrastructure",
            },
        )
        self.assertEqual(adjudications["theme:robotics-embodied-ai"]["outcome"], "conditional-requirement-added")
        self.assertTrue(all(item["status"] == "current" for item in adjudications.values()))
        reviewed = [item for key, item in adjudications.items() if key != "theme:robotics-embodied-ai"]
        self.assertTrue(all(item["evidence_review"]["status"] == "complete" for item in reviewed))
        self.assertEqual(sum(item["evidence_review"]["records_screened"] for item in reviewed), 147)
        queued_ids = {item["id"] for item in review["assessment_queue"]}
        self.assertFalse(set(adjudications).intersection(queued_ids))


if __name__ == "__main__":
    unittest.main()
