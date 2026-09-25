import unittest
from pathlib import Path

import yaml

from pipeline.classify import classify_record, classify_text, validate_classification_policy


ROOT = Path(__file__).resolve().parents[1]


class ClassificationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = yaml.safe_load((ROOT / "config/keywords.yml").read_text(encoding="utf-8"))
        cls.keywords = config["themes"]
        cls.policy = yaml.safe_load((ROOT / "config/classification-policy.yml").read_text(encoding="utf-8"))
        validate_classification_policy(cls.policy)

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

    def test_short_terms_use_word_boundaries(self):
        self.assertIn("skills-integrations", classify_text("An MCP server exposes tools.", self.keywords))
        self.assertNotIn("skills-integrations", classify_text("A compliance report was published.", self.keywords))
        self.assertIn("robotics-embodied-ai", classify_text("A VLA policy controls a robot.", self.keywords))
        self.assertNotIn("robotics-embodied-ai", classify_text("The novel argument was accepted.", self.keywords))

    def test_gap_vocabulary_maps_to_specific_themes(self):
        text = "Post-training uses GRPO; the served model relies on a KV cache and speculative decoding."
        themes = classify_text(text, self.keywords)
        self.assertIn("training-self-improvement", themes)
        self.assertIn("frontier-inference-infrastructure", themes)

    def test_selective_vocabulary_covers_inspected_recurring_clusters(self):
        cases = {
            "An LLM inference optimization guide": "frontier-inference-infrastructure",
            "An OpenAI agent swarm attacked a package registry": "agent-harnesses",
            "A multi-tenant agent runtime blocks exfiltration": "assurance-infrastructure",
            "Knowledge refresh for production RAG": "document-knowledge-systems",
            "A benchmark for long-term memory": "memory-context",
            "A robot foundation model": "robotics-embodied-ai",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertIn(expected, classify_text(text, self.keywords))

    def test_second_pass_maps_only_precise_cluster_vocabulary(self):
        cases = {
            "Scaling federated learning across private clients": {
                "training-self-improvement", "proprietary-data-boundary",
            },
            "Claude Code exposed an AI coding CI bottleneck": {"coding-agents"},
            "A jailbreak revealed a model safety failure": {"assurance-infrastructure"},
            "CUDA GPU kernels improve inference-time compute": {"frontier-inference-infrastructure"},
            "Multi-vector embedding models for information extraction": {"document-knowledge-systems"},
            "A cross-embodiment robot navigation system for robotics": {"robotics-embodied-ai"},
            "A forward-deployed engineer builds an enterprise workflow": {"enterprise-vertical-ai"},
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertTrue(expected.issubset(classify_text(text, self.keywords)))

    def test_generic_agent_and_model_brand_language_remains_unclassified(self):
        for text in (
            "AI agents are changing quickly",
            "A reaction to the latest Claude and Gemini releases",
        ):
            with self.subTest(text=text):
                self.assertEqual(classify_text(text, self.keywords), [])

    def test_general_community_material_is_explicitly_out_of_scope(self):
        result = classify_record(
            {
                "source_id": "hacker-news",
                "source_type": "community",
                "title": "Show HN: A community DVD lending library",
                "summary": "Borrow films from people nearby.",
                "tags": [],
            },
            self.keywords,
            self.policy,
        )
        self.assertEqual(result["disposition"], "out-of-scope")
        self.assertEqual(result["rule_id"], "community-no-ai-system-signal")

    def test_unmatched_research_stays_in_review(self):
        result = classify_record(
            {
                "source_id": "arxiv",
                "source_type": "paper",
                "title": "A novel AI architecture without reviewed taxonomy vocabulary",
                "summary": "Potentially relevant research should remain visible for review.",
                "tags": [],
            },
            self.keywords,
            self.policy,
        )
        self.assertEqual(result["disposition"], "classification-review")

    def test_precise_theme_match_wins_before_exclusion(self):
        result = classify_record(
            {
                "source_id": "yc-companies",
                "source_type": "company-directory",
                "title": "A robot foundation model company",
                "summary": "",
                "tags": [],
            },
            self.keywords,
            self.policy,
        )
        self.assertEqual(result["disposition"], "classified")
        self.assertIn("robotics-embodied-ai", result["theme_ids"])

    def test_inspected_publisher_housekeeping_is_out_of_scope(self):
        cases = (
            {
                "source_id": "yc-essays",
                "source_type": "operator-essay",
                "title": "Two people join YC as General Partners",
            },
            {
                "source_id": "greylock-essays",
                "source_type": "investor-essay",
                "title": "Introducing Greylock 18",
            },
        )
        for row in cases:
            with self.subTest(title=row["title"]):
                result = classify_record({**row, "summary": "", "tags": []}, self.keywords, self.policy)
                self.assertEqual(result["disposition"], "out-of-scope")


if __name__ == "__main__":
    unittest.main()
