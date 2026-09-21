import unittest
from datetime import datetime, timezone

from pipeline.score import score_theme


class ThemeScoreTests(unittest.TestCase):
    def test_empty_theme_is_unobserved_zero_components(self):
        score = score_theme([])
        self.assertEqual(score.total, 0)

    def test_cross_source_evidence_increases_breadth(self):
        now = datetime(2026, 9, 20, tzinfo=timezone.utc)
        one_source = [{"published_at": "2026-09-18T00:00:00+00:00", "source_type": "paper"}]
        two_sources = one_source + [{"published_at": "2026-09-17T00:00:00+00:00", "source_type": "repository"}]
        self.assertGreater(score_theme(two_sources, now).breadth, score_theme(one_source, now).breadth)


if __name__ == "__main__":
    unittest.main()
