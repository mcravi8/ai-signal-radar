import json
import unittest
from pathlib import Path

from pipeline.export_public import validate_public_payload


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/public/alphasignal-research.json"


class AlphaSignalPublicDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_reviewed_corpus_is_present(self):
        meta = self.payload["meta"]
        self.assertEqual(meta["email_count"], 129)
        self.assertEqual(meta["unique_catalog_records"], 888)
        self.assertEqual(len(self.payload["findings"]), 5)
        self.assertEqual(len(self.payload["trends"]), 15)
        self.assertEqual(len(self.payload["projects"]), 20)

    def test_scores_remain_separate(self):
        self.assertIn("score", self.payload["trends"][0])
        self.assertIn("opportunity_score", self.payload["projects"][0])
        self.assertEqual(self.payload["trends"][0]["score"]["total"], 89)
        self.assertEqual(self.payload["projects"][0]["opportunity_score"], 94)

    def test_public_boundary(self):
        validate_public_payload(self.payload)
        serialized = json.dumps(self.payload).lower()
        for blocked in ("mail.google.com", "authuser", "gmail_url", "message_id", "newsletter_statement"):
            self.assertNotIn(blocked, serialized)


if __name__ == "__main__":
    unittest.main()
