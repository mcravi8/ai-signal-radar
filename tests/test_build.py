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


if __name__ == "__main__":
    unittest.main()
