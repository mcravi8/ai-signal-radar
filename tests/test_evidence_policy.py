import json
import unittest
from pathlib import Path

import yaml

from pipeline.evidence_policy import build_operating_model, run_calibration, validate_policy
from pipeline.export_public import validate_public_payload


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
        self.assertEqual(self.results["simulation-first-physical-ai"]["maturity"], "experimental")
        self.assertEqual(self.results["governed-proprietary-data-boundary"]["maturity"], "experimental")
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
        self.assertEqual(
            {link["evidence_id"] for link in excluded},
            {"arxiv:2609.21774v1", "sequoia-essays:8a2fe18efd08a18eea8c"},
        )
        self.assertTrue(all(link["exclusion_reason"] for link in excluded))

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

    def test_candidate_reviews_update_existing_requirement_evidence_maps(self):
        cases = {case["id"]: case for case in self.calibration["cases"]}
        modular_ids = {link["evidence_id"] for link in cases["modular-agent-operating-stack"]["evidence_links"]}
        evaluation_ids = {link["evidence_id"] for link in cases["evaluation-release-gates"]["evidence_links"]}
        ownership_ids = {link["evidence_id"] for link in cases["bounded-workflow-ownership"]["evidence_links"]}
        routing_ids = {link["evidence_id"] for link in cases["heterogeneous-model-routing"]["evidence_links"]}

        self.assertIn("arxiv:2609.20804v1", modular_ids)
        self.assertIn("arxiv:2609.21843v1", modular_ids)
        self.assertIn("arxiv:2609.20812v1", evaluation_ids)
        self.assertIn("arxiv:2609.22049v1", ownership_ids)
        self.assertIn("arxiv:2609.20497v1", routing_ids)
        self.assertIn("sequoia-essays:8a2fe18efd08a18eea8c", routing_ids)

    def test_candidate_reviews_do_not_promote_without_operational_proof(self):
        self.assertEqual(self.results["modular-agent-operating-stack"]["maturity"], "emerging")
        self.assertEqual(self.results["evaluation-release-gates"]["maturity"], "experimental")
        self.assertEqual(self.results["heterogeneous-model-routing"]["maturity"], "experimental")
        self.assertEqual(self.results["bounded-workflow-ownership"]["maturity"], "narrative")

    def test_public_operating_model_explains_the_practice(self):
        payload = build_operating_model(self.policy, self.calibration, self.research)
        validate_public_payload(payload)
        self.assertEqual(payload["meta"]["requirement_count"], 8)
        for requirement in payload["requirements"]:
            self.assertGreater(len(requirement["description"]), 120)
            self.assertGreaterEqual(len(requirement["what_it_looks_like"]), 3)
            self.assertTrue(requirement["applicable_to"])
            self.assertTrue(requirement["evidence"])

    def test_physical_ai_requirement_is_conditional_and_reviews_counterevidence(self):
        case = next(
            case for case in self.calibration["cases"] if case["id"] == "simulation-first-physical-ai"
        )
        self.assertIn("not a general requirement", case["applicable_to"])
        self.assertTrue(case["gate_inputs"]["counterevidence_reviewed"])
        self.assertTrue(any(link["relationship"] == "counterevidence" for link in case["evidence_links"]))

    def test_enterprise_data_boundary_is_experimental_and_reviews_leakage(self):
        case = next(
            case for case in self.calibration["cases"] if case["id"] == "governed-proprietary-data-boundary"
        )
        result = self.results["governed-proprietary-data-boundary"]
        self.assertEqual(result["maturity"], "experimental")
        self.assertIn(
            "operational_adoption is low; requires moderate",
            result["gate_results"]["emerging"]["failures"],
        )
        self.assertTrue(case["gate_inputs"]["counterevidence_reviewed"])
        self.assertIn(
            "arxiv:2609.21686v1",
            {link["evidence_id"] for link in case["evidence_links"] if link["relationship"] == "counterevidence"},
        )

    def test_tracked_public_artifact_matches_reviewed_cases(self):
        payload = json.loads((ROOT / "data/public/operating-model.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {item["id"] for item in payload["requirements"]},
            {case["id"] for case in self.calibration["cases"]},
        )


if __name__ == "__main__":
    unittest.main()
