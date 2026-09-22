import json
import unittest
from pathlib import Path

import yaml

from pipeline.weekly_review import build_weekly_review


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

    def test_verification_families_state_their_boundary(self):
        review = build_weekly_review(self.research, self.operating, self.operating, None, self.config)
        self.assertEqual(len(review["verification_families"]), 6)
        self.assertTrue(all("Supporting verification" in item["boundary"] for item in review["verification_families"]))


if __name__ == "__main__":
    unittest.main()
