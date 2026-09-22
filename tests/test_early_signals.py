import unittest
from datetime import datetime, timedelta, timezone

from pipeline.research import _signal_movement, _signal_snapshot


class EarlySignalLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.as_of = datetime(2026, 9, 22, tzinfo=timezone.utc)
        self.sources = {
            "lab-a": {"channel": "first-party-lab"},
            "lab-b": {"channel": "first-party-lab"},
            "paper": {"channel": "paper"},
            "repo": {"channel": "repository"},
            "expert": {"channel": "expert-social"},
            "investor": {"channel": "investor-essay"},
        }

    def item(self, source_id, days_ago, suffix):
        return {
            "id": f"{source_id}-{suffix}",
            "source_id": source_id,
            "source_type": self.sources[source_id]["channel"],
            "published_at": (self.as_of - timedelta(days=days_ago)).isoformat(),
        }

    def test_established_requires_breadth_and_persistence(self):
        items = [
            self.item("lab-a", 5, "a"),
            self.item("lab-b", 8, "b"),
            self.item("paper", 10, "c"),
            self.item("repo", 12, "d"),
            self.item("expert", 14, "e"),
            self.item("investor", 40, "f"),
        ]
        snapshot = _signal_snapshot(items, self.sources, self.as_of)
        self.assertEqual(snapshot["stage"], "established")
        self.assertEqual(snapshot["family_count"], 5)
        self.assertEqual(snapshot["source_count"], 6)
        self.assertEqual(snapshot["active_periods"], 2)

    def test_fading_requires_no_recent_support(self):
        snapshot = _signal_snapshot([self.item("paper", 45, "old")], self.sources, self.as_of)
        self.assertEqual(snapshot["stage"], "fading")

    def test_movement_uses_non_overlapping_fourteen_day_periods(self):
        items = [
            self.item("paper", 40, "history"),
            self.item("paper", 20, "previous"),
            self.item("paper", 8, "current-a"),
            self.item("repo", 6, "current-b"),
            self.item("lab-a", 4, "current-c"),
        ]
        dated = sorted((datetime.fromisoformat(item["published_at"]), item) for item in items)
        movement = _signal_movement(dated, self.as_of, "corroborating")
        self.assertEqual(movement["movement"], "accelerating")
        self.assertEqual(movement["current_evidence_count"], 3)
        self.assertEqual(movement["previous_evidence_count"], 1)
        self.assertEqual(movement["evidence_change"], 2)


if __name__ == "__main__":
    unittest.main()
