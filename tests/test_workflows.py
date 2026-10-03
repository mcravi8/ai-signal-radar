import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def test_data_writers_share_one_concurrency_group(self):
        for name in ("collect-weekly.yml", "synthesize-weekly.yml"):
            with self.subTest(workflow=name):
                text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
                self.assertIn("group: radar-data-writer", text)
                self.assertIn("cancel-in-progress: false", text)

    def test_pages_deploy_has_one_trigger_after_synthesis(self):
        text = (ROOT / ".github/workflows/deploy-dashboard.yml").read_text(encoding="utf-8")
        self.assertIn('"data/public/**"', text)
        self.assertNotIn("workflow_run:", text)

    def test_weekly_collector_name_matches_its_schedule(self):
        self.assertTrue((ROOT / ".github/workflows/collect-weekly.yml").exists())
        self.assertFalse((ROOT / ".github/workflows/collect-daily.yml").exists())


if __name__ == "__main__":
    unittest.main()
