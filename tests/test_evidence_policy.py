import json
import unittest
from pathlib import Path

import yaml

from pipeline.evidence_policy import run_calibration, validate_policy


ROOT = Path(__file__).resolve().parents[1]


class EvidencePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = yaml.safe_load((ROOT / "config/evidence-policy.yml").read_text(encoding="utf-8"))
        cls.calibration = yaml.safe_load((ROOT / "config/evidence-policy-calibration.yml").read_text(encoding="utf-8"))
        cls.research = json.loads((ROOT / cls.calibration["dataset"]).read_text(encoding="utf-8"))
        cls.results = {item["id"]: item for item in run_calibration(cls.policy, cls.calibration, cls.research)}

    def test_policy_preserves_locked_levels_and_maturity_states(self):
        validate_policy(self.policy)
        self.assertEqual(self.policy["public_levels"], ["not-observed", "low", "moderate", "strong"])
        self.assertEqual(
            self.policy["maturity_order"],
            ["narrative", "experimental", "emerging", "established", "baseline"],
        )

    def test_calibration_cases_match_reviewed_outcomes(self):
        self.assertEqual(self.results["evaluation-release-gates"]["maturity"], "experimental")
        self.assertEqual(self.results["heterogeneous-model-routing"]["maturity"], "experimental")
        self.assertEqual(self.results["ai-native-gtm"]["maturity"], "narrative")
        self.assertEqual(self.results["modular-agent-operating-stack"]["maturity"], "emerging")
        self.assertEqual(self.results["shared-operational-context"]["maturity"], "experimental")
        self.assertEqual(self.results["bounded-workflow-ownership"]["maturity"], "narrative")
        self.assertTrue(all(result["matches_expected"] for result in self.results.values()))

    def test_operational_proof_blocks_premature_promotion(self):
        evaluation = self.results["evaluation-release-gates"]
        routing = self.results["heterogeneous-model-routing"]
        self.assertIn("operational_adoption is low; requires moderate", evaluation["gate_results"]["emerging"]["failures"])
        self.assertIn("operational_adoption is low; requires moderate", routing["gate_results"]["emerging"]["failures"])

    def test_attention_does_not_promote_ai_native_gtm(self):
        gtm = self.results["ai-native-gtm"]
        self.assertFalse(gtm["gate_results"]["experimental"]["passed"])
        self.assertIn("technical_reality is not-observed; requires moderate", gtm["gate_results"]["experimental"]["failures"])

    def test_false_positive_is_explicitly_excluded(self):
        routing_case = next(case for case in self.calibration["cases"] if case["id"] == "heterogeneous-model-routing")
        excluded = [link for link in routing_case["evidence_links"] if link["relationship"] == "excluded"]
        self.assertEqual([link["evidence_id"] for link in excluded], ["arxiv:2609.21774v1"])
        self.assertTrue(excluded[0]["exclusion_reason"])

    def test_modular_stack_is_the_only_emerging_requirement(self):
        emerging = [result["id"] for result in self.results.values() if result["maturity"] == "emerging"]
        self.assertEqual(emerging, ["modular-agent-operating-stack"])
        modular = self.results["modular-agent-operating-stack"]
        self.assertFalse(modular["gate_results"]["established"]["passed"])
        self.assertIn(
            "operational_adoption is moderate; requires strong",
            modular["gate_results"]["established"]["failures"],
        )

    def test_counterevidence_review_has_an_explicit_record(self):
        modular_case = next(
            case for case in self.calibration["cases"] if case["id"] == "modular-agent-operating-stack"
        )
        self.assertTrue(modular_case["gate_inputs"]["counterevidence_reviewed"])
        self.assertTrue(any(link["relationship"] == "counterevidence" for link in modular_case["evidence_links"]))


if __name__ == "__main__":
    unittest.main()
