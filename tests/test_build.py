import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteBuildTests(unittest.TestCase):
    def test_static_build_contains_entrypoint_and_data(self):
        subprocess.run([sys.executable, "scripts/build_site.py"], cwd=ROOT, check=True)
        self.assertTrue((ROOT / "dist/index.html").exists())
        self.assertTrue((ROOT / "dist/data/dashboard.json").exists())
        self.assertTrue((ROOT / "dist/data/alphasignal-research.json").exists())
        self.assertTrue((ROOT / "dist/data/research.json").exists())
        self.assertTrue((ROOT / "dist/data/operating-model.json").exists())
        self.assertTrue((ROOT / "dist/data/weekly-review.json").exists())
        self.assertTrue((ROOT / "dist/data/discovery-review.json").exists())
        html = (ROOT / "dist/index.html").read_text(encoding="utf-8")
        app = (ROOT / "dist/app.js").read_text(encoding="utf-8")
        self.assertIn('id="source-type"', html)
        self.assertIn('data-route="operating-model"', html)
        self.assertIn('data-route="weekly-review"', html)
        self.assertIn('data-route="discovery"', html)
        self.assertIn('id="merge-suggestions"', html)
        self.assertIn('id="decision-review"', html)
        self.assertIn('id="requirement-detail"', html)
        self.assertIn("sourceChannelOrder", app)
        self.assertIn("source-group", app)
        self.assertIn("renderOperatingModel", app)
        self.assertIn("renderWeeklyReview", app)
        self.assertIn("renderDiscovery", app)
        self.assertIn("discovery-review.json", app)
        self.assertIn("what_it_looks_like", app)


if __name__ == "__main__":
    unittest.main()
