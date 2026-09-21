import json
import unittest
from pathlib import Path

from pipeline.export_public import validate_public_payload


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/public/research.json"


class CrossSourceResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_every_active_source_uses_common_evidence_contract(self):
        required = {
            "id", "source_id", "source_type", "evidence_kind", "title", "published_at",
            "theme_ids", "stack_layers", "support_count", "monthly_counts", "provenance",
        }
        self.assertGreaterEqual(self.payload["meta"]["active_source_count"], 7)
        expected_sources = {"alphasignal", "arxiv", "huggingface-papers", "github", "hacker-news", "yc-essays", "sequoia-essays", "menlo-ventures", "greylock-essays", "radical-ventures"}
        self.assertTrue(expected_sources.issubset({item["source_id"] for item in self.payload["evidence"]}))
        for item in self.payload["evidence"]:
            self.assertTrue(required.issubset(item), item["id"])

    def test_cross_source_theme_analysis_preserves_provenance(self):
        observed = [theme for theme in self.payload["themes"] if theme["evidence_count"]]
        self.assertGreaterEqual(len(observed), 18)
        self.assertTrue(any(theme["source_count"] >= 4 for theme in observed))
        for theme in observed:
            self.assertEqual(theme["source_count"], len(theme["source_breakdown"]))
            self.assertIsNotNone(theme["source_concentration"])
            self.assertIsNotNone(theme["score"])

    def test_unobserved_themes_are_not_scored(self):
        unobserved = [theme for theme in self.payload["themes"] if theme["maturity"] == "unobserved"]
        self.assertGreaterEqual(len(unobserved), 1)
        for theme in unobserved:
            self.assertIsNone(theme["score"])
            self.assertEqual(theme["support_units"], 0)

    def test_emerging_category_pool_can_supply_three_candidates(self):
        candidates = [theme for theme in self.payload["themes"] if theme["maturity"] in {"source-specific", "emerging"}]
        self.assertGreaterEqual(len(candidates), 3)

    def test_project_catalog_combines_reviewed_and_discovered_projects(self):
        reviewed = [project for project in self.payload["projects"] if project["review_status"] == "reviewed"]
        discovered = [project for project in self.payload["projects"] if project["review_status"] == "unreviewed"]
        self.assertEqual(len(reviewed), 20)
        self.assertGreater(len(discovered), 100)
        self.assertTrue(all(project["opportunity_score"] is None for project in discovered))
        self.assertTrue(all(project["source_ids"] for project in self.payload["projects"]))

    def test_alphasignal_is_one_analysis_and_one_source(self):
        analyses = {analysis["id"]: analysis for analysis in self.payload["analyses"]}
        self.assertIn("cross-source-landscape", analyses)
        self.assertIn("alphasignal-corpus", analyses)
        self.assertIn("operator-narratives", analyses)
        self.assertEqual(analyses["operator-narratives"]["status"], "complete")
        self.assertGreaterEqual(len(analyses["operator-narratives"]["source_ids"]), 5)
        self.assertEqual(analyses["operator-narratives"]["classified_source_count"], 5)
        self.assertTrue(analyses["operator-narratives"]["theme_summary"])
        narrative_ids = set(analyses["operator-narratives"]["evidence_ids"])
        narrative_evidence = [item for item in self.payload["evidence"] if item["id"] in narrative_ids]
        self.assertEqual(len(narrative_evidence), analyses["operator-narratives"]["evidence_count"])
        self.assertFalse(any(item["title"].casefold().startswith("welcome") for item in narrative_evidence))
        self.assertTrue(analyses["operator-narratives"]["executive_summary"])
        findings = analyses["operator-narratives"]["findings"]
        self.assertGreaterEqual(len(findings), 5)
        self.assertTrue(all({"analysis", "why_it_matters", "workflow_opportunity", "caveat", "evidence_ids"}.issubset(finding) for finding in findings))
        self.assertTrue(all(set(finding["evidence_ids"]).issubset(narrative_ids) for finding in findings))
        gtm_watch = next(finding for finding in findings if finding["id"] == "ai-native-gtm-watch")
        self.assertEqual(gtm_watch["strength"], "watch")
        self.assertEqual(gtm_watch["metrics"]["publishers"], 1)
        self.assertTrue({"yc-essays", "sequoia-essays", "menlo-ventures", "greylock-essays", "radical-ventures"}.issubset(analyses["operator-narratives"]["source_ids"]))
        self.assertGreater(len(analyses["cross-source-landscape"]["source_ids"]), len(analyses["alphasignal-corpus"]["source_ids"]))

    def test_public_boundary(self):
        validate_public_payload(self.payload)

    def test_active_sources_publish_official_brand_metadata(self):
        branded = [source for source in self.payload["sources"] if source["status"] == "active"]
        self.assertTrue(branded)
        self.assertTrue(all(source.get("homepage_url", "").startswith("https://") for source in branded))
        self.assertTrue(all(source.get("logo_url", "").startswith("https://") for source in branded))


if __name__ == "__main__":
    unittest.main()
