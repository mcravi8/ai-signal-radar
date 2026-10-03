import json
import tempfile
import unittest
from pathlib import Path

from pipeline.collection_health import build_collection_health


class CollectionHealthTests(unittest.TestCase):
    def test_legacy_receipt_keeps_failed_collection_separate_from_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "2026-09-26"
            run.mkdir()
            (run / "status.json").write_text(json.dumps({
                "collected_at": "2026-09-26T11:28:59+00:00",
                "items": 1,
                "added": 1,
                "errors": ["arxiv: HTTP Error 406: Not Acceptable"],
            }), encoding="utf-8")
            (run / "items.jsonl").write_text(
                json.dumps({"source_id": "github"}) + "\n",
                encoding="utf-8",
            )
            health = build_collection_health(root, [
                {"id": "arxiv", "collection": "api"},
                {"id": "github", "collection": "api"},
                {"id": "manual-source", "collection": "manual"},
            ])

        self.assertEqual(health["status"], "degraded")
        self.assertEqual(health["failed_source_ids"], ["arxiv"])
        self.assertEqual(health["sources"]["arxiv"]["status"], "failed")
        self.assertEqual(health["sources"]["github"]["status"], "healthy")
        self.assertEqual(health["sources"]["manual-source"]["status"], "not-automated")

    def test_structured_receipt_preserves_per_source_zero_result_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "2026-10-03"
            run.mkdir()
            (run / "newsletter-status.json").write_text(json.dumps({
                "collected_at": "2026-10-03T02:00:00+00:00",
                "items": 0,
                "errors": [],
                "collectors": [{"source_id": "agent-news", "status": "healthy", "items": 0}],
            }), encoding="utf-8")
            health = build_collection_health(root, [{"id": "agent-news", "collection": "agentmail"}])

        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["sources"]["agent-news"]["status"], "healthy")
        self.assertEqual(health["sources"]["agent-news"]["items"], 0)
