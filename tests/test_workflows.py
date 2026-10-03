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

    def test_pages_deploy_runs_once_after_successful_synthesis(self):
        text = (ROOT / ".github/workflows/deploy-dashboard.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_run:", text)
        self.assertIn('workflows: ["Synthesize weekly radar"]', text)
        self.assertNotIn("  push:", text)
        self.assertIn("workflow_run.conclusion == 'success'", text)

    def test_frontend_changes_enter_the_single_synthesis_then_deploy_path(self):
        text = (ROOT / ".github/workflows/synthesize-weekly.yml").read_text(encoding="utf-8")
        self.assertIn("- site/**", text)
        self.assertIn("- scripts/build_site.py", text)
        self.assertIn("- schemas/**", text)

    def test_weekly_collector_name_matches_its_schedule(self):
        self.assertTrue((ROOT / ".github/workflows/collect-weekly.yml").exists())
        self.assertFalse((ROOT / ".github/workflows/collect-daily.yml").exists())


if __name__ == "__main__":
    unittest.main()
