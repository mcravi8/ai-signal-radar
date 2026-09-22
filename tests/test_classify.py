import unittest
from pathlib import Path

import yaml

from pipeline.classify import classify_text


ROOT = Path(__file__).resolve().parents[1]


class ClassificationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = yaml.safe_load((ROOT / "config/keywords.yml").read_text(encoding="utf-8"))
        cls.keywords = config["themes"]

    def test_jev_is_recognized_as_a_specialized_decision_model(self):
        themes = classify_text(
            "Jev is a non-autoregressive System One model for fast typed decisions.",
            self.keywords,
        )
        self.assertIn("small-specialized-models", themes)

    def test_jev_use_cases_retain_specific_architecture_themes(self):
        themes = classify_text(
            "Agent middleware uses Jev for semantic routing and a tool-call guardrail.",
            self.keywords,
        )
        self.assertTrue({"small-specialized-models", "model-routing", "agent-harnesses", "assurance-infrastructure"}.issubset(themes))


if __name__ == "__main__":
    unittest.main()
