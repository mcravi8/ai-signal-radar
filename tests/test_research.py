import json
import unittest
from collections import Counter
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
        self.assertGreaterEqual(self.payload["meta"]["active_source_count"], 28)
        expected_sources = {
            "alphasignal", "arxiv", "huggingface-papers", "github", "hacker-news",
            "yc-essays", "sequoia-essays", "menlo-ventures", "greylock-essays", "radical-ventures",
            "openai-news", "anthropic-news-research", "deepmind-blog", "microsoft-research-blog",
            "nvidia-developer-blog", "mistral-news", "huggingface-blog", "aws-machine-learning-blog",
            "cloudflare-ai-blog",
            "latent-space", "import-ai", "the-batch", "interconnects", "last-week-in-ai",
            "simon-willison", "chip-huyen", "eugene-yan", "lilian-weng",
        }
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
        for theme in unobserved:
            self.assertIsNone(theme["score"])
            self.assertEqual(theme["support_units"], 0)

    def test_emerging_category_pool_can_supply_three_candidates(self):
        candidates = [theme for theme in self.payload["themes"] if theme["maturity"] in {"source-specific", "emerging"}]
        self.assertGreaterEqual(len(candidates), 3)

    def test_project_catalog_combines_reviewed_and_discovered_projects(self):
        reviewed = [project for project in self.payload["projects"] if project["review_status"] == "reviewed"]
        queued = [project for project in self.payload["projects"] if project["review_status"] == "queued"]
        discovered = [project for project in self.payload["projects"] if project["review_status"] == "discovered"]
        self.assertEqual(len(reviewed), 25)
        self.assertEqual(len(queued), 25)
        self.assertGreater(len(discovered), 100)
        self.assertTrue(all(project["opportunity_score"] is None for project in queued + discovered))
        self.assertTrue(all(project["source_ids"] for project in self.payload["projects"]))
        self.assertTrue(all(project["theme_ids"] for project in queued))
        self.assertTrue(all(project["review_priority"] is not None for project in self.payload["projects"]))
        signature_counts = Counter(tuple(project["theme_ids"]) for project in queued)
        self.assertLessEqual(max(signature_counts.values()), 3)
        public_reviews = [project for project in reviewed if project.get("verification_level")]
        self.assertEqual(len(public_reviews), 5)
        self.assertTrue(all(project.get("review_basis") for project in public_reviews))
        self.assertTrue(all("github" in project["source_ids"] for project in public_reviews))
        blindspot = next(project for project in public_reviews if project["name"] == "sadia-sigma-lab/BLINDSPOT")
        self.assertIn("arxiv", blindspot["source_ids"])

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

    def test_first_party_lab_feeds_are_active_and_disclosed(self):
        labs = [source for source in self.payload["sources"] if source.get("channel") == "first-party-lab"]
        self.assertEqual(len(labs), 9)
        self.assertTrue(all(source["status"] == "active" for source in labs))
        self.assertTrue(all(source["normalized_evidence_count"] > 0 for source in labs))
        self.assertTrue(all(source["commercial_bias"] == "first-party" for source in labs))
        self.assertTrue(all(source["evidence_role"] == "first-party-claim" for source in labs))

    def test_verification_feeds_do_not_turn_first_observation_into_publication_recency(self):
        yc_companies = [item for item in self.payload["evidence"] if item["source_id"] == "yc-companies"]
        yc_jobs = [item for item in self.payload["evidence"] if item["source_id"] == "yc-jobs"]
        self.assertEqual(len(yc_companies), 50)
        self.assertTrue(yc_jobs)
        self.assertTrue(all(not item["published_at"] and item["observed_at"] for item in yc_companies))
        self.assertTrue(all(item["verification"]["date_basis"] == "first-observed" for item in yc_companies))
        self.assertTrue(all(item["verification"]["date_basis"] == "approximate-public-age" for item in yc_jobs))

    def test_public_newsletters_and_practitioner_feeds_are_typed(self):
        channels = {"expert-newsletter", "curated-newsletter", "practitioner-blog"}
        sources = [source for source in self.payload["sources"] if source.get("channel") in channels]
        self.assertEqual(len(sources), 9)
        self.assertTrue(all(source["status"] == "active" for source in sources))
        self.assertTrue(all(source["normalized_evidence_count"] > 0 for source in sources))
        roles = {source["evidence_role"] for source in sources}
        self.assertEqual(roles, {"expert-interpretation", "curated-roundup"})
        roundups = [source for source in sources if source["evidence_role"] == "curated-roundup"]
        self.assertEqual({source["id"] for source in roundups}, {"the-batch", "last-week-in-ai"})

    def test_bluesky_experts_feed_a_separate_analysis(self):
        analyses = {analysis["id"]: analysis for analysis in self.payload["analyses"]}
        pulse = analyses["expert-pulse"]
        self.assertIn(pulse["status"], {"configured", "active"})
        self.assertIn("engagement", pulse["interpretation_note"].casefold())
        self.assertTrue(pulse["executive_summary"])
        self.assertGreaterEqual(len(pulse["findings"]), 3)
        self.assertTrue(all({"analysis", "why_it_matters", "workflow_opportunity", "caveat", "evidence_ids"}.issubset(finding) for finding in pulse["findings"]))
        bluesky_sources = [
            source for source in self.payload["sources"]
            if source.get("channel") == "expert-social"
        ]
        self.assertEqual(len(bluesky_sources), 8)
        self.assertTrue(all(source["evidence_role"] == "expert-observation" for source in bluesky_sources))
        self.assertTrue(all("bsky.social/about/brand-assets/" in source["logo_url"] for source in bluesky_sources))

    def test_engineering_atlas_exposes_quality_and_review_states(self):
        atlas = self.payload["engineering_atlas"]
        self.assertGreaterEqual(len(atlas["concepts"]), 10)
        self.assertGreater(atlas["quality"]["classification_coverage"], 0.2)
        self.assertEqual(
            atlas["quality"]["classified_public_records"] + atlas["quality"]["classification_review_records"],
            self.payload["meta"]["public_record_count"],
        )
        self.assertEqual(atlas["quality"]["queued_projects"], 25)
        self.assertEqual(atlas["quality"]["reviewed_projects"], 25)
        self.assertIn("not a direct collector-uptime check", atlas["freshness_note"])
        self.assertTrue(all({"project_count", "reviewed_project_count", "queued_project_count"}.issubset(concept) for concept in atlas["concepts"]))
        active_sources = [source for source in self.payload["sources"] if source["status"] == "active"]
        self.assertTrue(all(source["last_observed_at"] for source in active_sources))
        self.assertTrue(all(source["freshness"] in {"recent", "aging", "historical"} for source in active_sources))
        self.assertTrue(all(item["disposition"] in {"classified", "classification-review"} for item in self.payload["evidence"]))
        audit = atlas["classification_audit"]
        self.assertEqual(audit["sample_size"], 120)
        self.assertEqual(audit["newly_classified_records"], 110)
        self.assertEqual(audit["current_unclassified_records"], atlas["quality"]["unclassified_public_records"])
        self.assertGreater(audit["post_audit_classification_coverage"], audit["baseline_classification_coverage"])

    def test_early_signal_tracker_separates_inference_from_evidence(self):
        analyses = {analysis["id"]: analysis for analysis in self.payload["analyses"]}
        tracker = analyses["early-signal-tracker"]
        self.assertEqual(tracker["status"], "active")
        self.assertGreaterEqual(tracker["direction_count"], 5)
        self.assertIn("not forecasts", tracker["executive_summary"].casefold())
        self.assertIn("source-family breadth", tracker["interpretation_note"].casefold())
        self.assertEqual(tracker["method"]["evidence_window_days"], 90)
        self.assertEqual(tracker["method"]["comparison_window_days"], 14)
        self.assertEqual(len(tracker["important_changes"]), 5)
        evidence_ids = {item["id"] for item in self.payload["evidence"]}
        required = {
            "hypothesis", "interpretation", "why_it_matters", "next_confirmation",
            "counter_signal", "stage", "previous_stage", "confidence", "source_families",
            "evidence_ids", "movement", "current_evidence_count", "previous_evidence_count",
            "evidence_change", "origin", "state_reason", "lifecycle_history",
        }
        for direction in tracker["directions"]:
            self.assertTrue(required.issubset(direction), direction["id"])
            self.assertIn(direction["stage"], {"weak-signal", "emerging", "corroborating", "established", "fading", "unobserved"})
            self.assertIn(direction["movement"], {"new", "accelerating", "resurfacing", "steady", "cooling", "fading"})
            self.assertTrue(set(direction["evidence_ids"]).issubset(evidence_ids))
            self.assertLessEqual(len(direction["evidence_ids"]), 8)
            self.assertEqual(direction["family_count"], len(direction["source_families"]))
            self.assertTrue(all(family["source_count"] > 0 for family in direction["source_families"]))
            self.assertEqual(direction["evidence_change"], direction["current_evidence_count"] - direction["previous_evidence_count"])
            self.assertEqual(len(direction["lifecycle_history"]), 8)
            self.assertEqual(
                [snapshot["as_of"] for snapshot in direction["lifecycle_history"]],
                sorted(snapshot["as_of"] for snapshot in direction["lifecycle_history"]),
            )
        self.assertTrue(set(tracker["important_changes"]).issubset({direction["id"] for direction in tracker["directions"]}))


if __name__ == "__main__":
    unittest.main()
