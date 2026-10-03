import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.collectors.events import parse_devpost, parse_event_json, parse_proceedings, parse_reviewed_social_issues
from pipeline.events import assign_event_ids, build_event_pulse, load_social_links, validate_event_config


ROOT = Path(__file__).resolve().parents[1]


class EventCollectorTests(unittest.TestCase):
    def test_event_json_applies_track_caps_and_keeps_event_context(self):
        source = {
            "id": "conference-program",
            "event_id": "example-event",
            "data_url": "https://example.com/sessions.json",
            "homepage_url": "https://example.com/event",
            "published_at": "2026-01-01",
            "include_types": ["session"],
            "priority_tracks": ["Evals", "Inference"],
            "max_per_track": 1,
            "limit": 5,
        }
        payload = json.dumps(
            {
                "sessions": [
                    {"title": "Eval one", "description": "A", "track": "Evals", "type": "session", "speakers": ["A"]},
                    {"title": "Eval two", "description": "B", "track": "Evals", "type": "session", "speakers": ["B"]},
                    {"title": "Route models", "description": "C", "track": "Inference", "type": "session", "speakers": ["C"]},
                    {"title": "Sponsor pitch", "track": "Evals", "type": "sponsor"},
                ]
            }
        ).encode()
        items = parse_event_json(source, payload)
        self.assertEqual([item.title for item in items], ["Eval one", "Route models"])
        self.assertTrue(all(item.event_ids == ["example-event"] for item in items))

    def test_proceedings_filter_returns_artifacts(self):
        source = {
            "id": "papers",
            "event_id": "example-event",
            "proceedings_url": "https://example.com/papers/",
            "published_at": "2026-01-01",
            "include_terms": ["agent"],
            "limit": 10,
        }
        payload = b'<a title="paper title" href="one.html">Agent Evaluation</a><a title="paper title" href="two.html">Vision Study</a>'
        items = parse_proceedings(source, payload)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].artifact_urls, ["https://example.com/papers/one.html"])

    def test_devpost_parser_retains_only_metadata(self):
        source = {
            "id": "projects",
            "event_id": "example-event",
            "published_at": "2026-01-02",
            "limit": 5,
        }
        payload = b'''<div class="gallery-item"><a class="link-to-software" href="https://devpost.com/software/demo"><h5>Demo</h5><p class="small tagline">A useful tool</p><img alt="Winner" /></a></div>'''
        items = parse_devpost(source, [payload])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Demo")
        self.assertTrue(items[0].metadata["winner"])
        self.assertNotIn("post_body", items[0].to_dict())

    def test_reviewed_issue_form_becomes_a_bounded_social_observation(self):
        config = yaml.safe_load((ROOT / "config/events.yml").read_text(encoding="utf-8"))
        issue = {
            "number": 12,
            "body": """### Event ID\n\nneurips-2025\n\n### Platform\n\nx\n\n### Public post URL\n\nhttps://x.com/person/status/1\n\n### Author name\n\nResearcher\n\n### Published date\n\n2025-12-10\n\n### Original observation\n\nThe author links a public evaluation repository.\n\n### Linked public artifacts\n\nhttps://github.com/example/eval\n""",
        }
        items = parse_reviewed_social_issues([issue], config)
        self.assertEqual(items[0].source_id, "x-event-links")
        self.assertEqual(items[0].event_ids, ["neurips-2025"])
        self.assertEqual(items[0].artifact_urls, ["https://github.com/example/eval"])


class EventPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = yaml.safe_load((ROOT / "config/events.yml").read_text(encoding="utf-8"))

    def test_repository_event_policy_is_valid(self):
        validate_event_config(self.config)
        self.assertEqual(sum(event["pilot"] for event in self.config["events"]), 3)

    def test_social_inbox_rejects_copied_post_body(self):
        payload = {
            "links": [{
                "id": "social:1",
                "platform": "x",
                "post_url": "https://x.com/person/status/1",
                "author_name": "Person",
                "published_at": "2026-01-01",
                "event_ids": ["neurips-2025"],
                "observation": "Short original observation.",
                "post_body": "Copied text",
            }]
        }
        with self.assertRaises(ValueError):
            load_social_links(payload, self.config)

    def test_alias_matching_is_date_bounded(self):
        rows = [
            {"id": "in", "source_id": "blog", "title": "NeurIPS 2025 notes", "summary": "", "tags": [], "published_at": "2025-12-20"},
            {"id": "out", "source_id": "blog", "title": "NeurIPS 2025 archive", "summary": "", "tags": [], "published_at": "2026-09-20"},
        ]
        assign_event_ids(rows, self.config)
        self.assertIn("neurips-2025", rows[0]["event_ids"])
        self.assertNotIn("neurips-2025", rows[1].get("event_ids", []))

    def test_later_artifact_is_linked_without_repeating_event_name(self):
        rows = [
            {
                "id": "event-project", "source_id": "genai-genesis-2026-projects", "source_type": "hackathon-project",
                "title": "Durable Agent", "url": "https://devpost.com/software/durable-agent", "published_at": "2026-03-15",
                "summary": "", "tags": [], "projects": ["Durable Agent"], "artifact_urls": [],
            },
            {
                "id": "later-repo", "source_id": "github", "source_type": "repository",
                "title": "team/durable-agent", "url": "https://github.com/team/durable-agent", "published_at": "2026-04-10",
                "summary": "", "tags": [], "projects": ["Durable Agent"], "artifact_urls": [],
            },
        ]
        assign_event_ids(rows, self.config)
        self.assertIn("genai-genesis-2026", rows[1]["event_ids"])

    def test_attention_and_substance_are_separate_and_echoes_collapse(self):
        config = {
            **self.config,
            "events": [{
                "id": "example-event",
                "name": "Example Event",
                "event_type": "developer-conference",
                "status": "completed",
                "start_date": "2026-01-01",
                "end_date": "2026-01-02",
                "location": "Online",
                "official_url": "https://example.com/event",
                "aliases": ["Example Event"],
                "source_ids": ["program"],
                "pilot": True,
                "review_windows_days": [30, 90],
                "sampling_note": "Bounded sample.",
                "framing": "Inspect the event without treating it as validation.",
            }],
        }
        evidence = [
            {
                "id": "one", "source_id": "program", "source_type": "event-session", "title": "Agent evals",
                "url": "https://example.com/event", "published_at": "2026-01-01", "event_ids": ["example-event"],
                "artifact_urls": [], "projects": [], "theme_ids": ["assurance"],
            },
            {
                "id": "echo", "source_id": "social", "source_type": "curated-social", "title": "Agent evals",
                "url": "https://x.com/a/status/1", "published_at": "2026-01-01", "event_ids": ["example-event"],
                "artifact_urls": [], "projects": [], "theme_ids": ["assurance"],
            },
        ]
        result = build_event_pulse(
            evidence,
            config,
            [{"id": "program", "channel": "event-program"}, {"id": "social", "channel": "curated-social"}],
            [{"id": "assurance", "name": "Assurance"}],
            as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )["analysis"]["events"][0]
        self.assertNotEqual(result["attention"]["score"], result["technical_substance"]["score"])
        self.assertEqual(result["independent_observation_count"], 1)
        self.assertEqual(result["echo_records_collapsed"], 1)
        self.assertEqual(result["independent_source_count"], 1)
        self.assertEqual(result["attention"]["components"]["source_breadth_points"], 8)
        self.assertEqual(result["technical_substance"]["components"]["artifact_points"], 0)
        self.assertEqual(result["persistence_checks"][-1]["status"], "not-observed")

    def test_social_artifact_url_collapses_with_the_artifact_record(self):
        config = {
            **self.config,
            "events": [{
                "id": "example-event", "name": "Example Event", "event_type": "developer-conference",
                "status": "completed", "start_date": "2026-01-01", "end_date": "2026-01-02",
                "location": "Online", "official_url": "https://example.com/event",
                "aliases": ["Example Event"], "source_ids": [], "pilot": True,
                "review_windows_days": [30, 90], "framing": "Inspect evidence.",
                "sampling_note": "Bounded sample.",
            }],
        }
        repository_url = "https://github.com/example/tool"
        evidence = [
            {
                "id": "repo", "source_id": "github", "source_type": "repository", "title": "example/tool",
                "url": repository_url, "published_at": "2026-01-03", "event_ids": ["example-event"],
                "artifact_urls": [], "projects": ["Tool"], "theme_ids": ["agents"],
            },
            {
                "id": "post", "source_id": "x-event-links", "source_type": "curated-social", "title": "Demo recap",
                "url": "https://x.com/example/status/1", "published_at": "2026-01-03", "event_ids": ["example-event"],
                "artifact_urls": [repository_url], "projects": [], "theme_ids": ["agents"],
            },
        ]
        event = build_event_pulse(
            evidence, config,
            [{"id": "github", "channel": "repository"}, {"id": "x-event-links", "channel": "curated-social"}],
            [{"id": "agents", "name": "Agents"}], as_of=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )["analysis"]["events"][0]
        self.assertEqual(event["independent_observation_count"], 1)
        self.assertEqual(event["artifact_count"], 1)
        self.assertEqual(event["independent_source_count"], 1)
        self.assertEqual(event["themes"][0]["evidence_count"], 1)

    def test_later_repost_of_an_event_artifact_is_not_persistence(self):
        config = {
            **self.config,
            "events": [{
                "id": "example-event", "name": "Example Event", "event_type": "research-conference",
                "status": "completed", "start_date": "2026-01-01", "end_date": "2026-01-02",
                "location": "Online", "official_url": "https://example.com/event",
                "aliases": ["Example Event"], "source_ids": ["proceedings"], "pilot": True,
                "review_windows_days": [30, 90], "framing": "Inspect evidence.",
                "sampling_note": "Bounded sample.",
            }],
        }
        paper_url = "https://example.com/paper"
        evidence = [
            {
                "id": "paper", "source_id": "proceedings", "source_type": "event-paper", "title": "Paper",
                "url": paper_url, "published_at": "2026-01-01", "event_ids": ["example-event"],
                "artifact_urls": [paper_url], "projects": [], "theme_ids": [],
            },
            {
                "id": "repost", "source_id": "x-event-links", "source_type": "curated-social", "title": "Paper recap",
                "url": "https://x.com/example/status/2", "published_at": "2026-01-20", "event_ids": ["example-event"],
                "artifact_urls": [paper_url], "projects": [], "theme_ids": [],
            },
        ]
        event = build_event_pulse(
            evidence, config,
            [{"id": "proceedings", "channel": "event-program"}, {"id": "x-event-links", "channel": "curated-social"}],
            [], as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )["analysis"]["events"][0]
        self.assertTrue(all(check["status"] == "not-observed" for check in event["persistence_checks"]))

    def test_uncollected_event_is_not_assessed_not_not_observed(self):
        config = {
            **self.config,
            "events": [{
                "id": "configured-event",
                "name": "Configured Event",
                "event_type": "vendor-conference",
                "status": "configured",
                "start_date": "2026-01-01",
                "end_date": "2026-01-02",
                "location": "Online",
                "official_url": "https://example.com/event",
                "aliases": ["Configured Event"],
                "source_ids": [],
                "pilot": False,
                "review_windows_days": [30, 90],
                "framing": "Wait for public evidence.",
                "sampling_note": "No sample collected.",
            }],
        }
        event = build_event_pulse(
            [], config, [], [], as_of=datetime(2026, 5, 1, tzinfo=timezone.utc)
        )["analysis"]["events"][0]
        self.assertEqual(event["attention"]["label"], "not-assessed")
        self.assertTrue(all(check["status"] == "not-assessed" for check in event["persistence_checks"]))

    def test_hackathon_pages_receive_partial_artifact_weight(self):
        config = {
            **self.config,
            "events": [{
                "id": "hackathon",
                "name": "Hackathon",
                "event_type": "hackathon",
                "status": "completed",
                "start_date": "2026-01-01",
                "end_date": "2026-01-02",
                "location": "Online",
                "official_url": "https://example.com/event",
                "aliases": ["Example Hackathon"],
                "source_ids": ["gallery"],
                "pilot": True,
                "review_windows_days": [30, 90],
                "framing": "Inspect project pages.",
                "sampling_note": "Bounded sample.",
            }],
        }
        evidence = [{
            "id": f"project-{index}", "source_id": "gallery", "source_type": "hackathon-project",
            "title": f"Project {index}", "url": f"https://example.com/project/{index}",
            "published_at": "2026-01-01", "event_ids": ["hackathon"],
            "artifact_urls": [f"https://example.com/project/{index}"], "projects": [f"Project {index}"],
            "theme_ids": [],
        } for index in range(30)]
        event = build_event_pulse(
            evidence, config, [{"id": "gallery", "channel": "hackathon-gallery"}], [],
            as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )["analysis"]["events"][0]
        self.assertEqual(event["artifact_count"], 30)
        self.assertEqual(event["weighted_artifact_count"], 15.0)
        self.assertLess(event["technical_substance"]["score"], 60)


if __name__ == "__main__":
    unittest.main()
