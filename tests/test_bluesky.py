import unittest
from pathlib import Path

import yaml

from pipeline.collectors.bluesky import Account, parse_feed
from pipeline.export_public import sanitize_item, validate_public_payload


ROOT = Path(__file__).resolve().parents[1]


class BlueskyCollectorTests(unittest.TestCase):
    def setUp(self):
        self.account = Account(
            source_id="expert-example",
            publisher_id="expert-example",
            display_name="Expert Example",
            handle="expert.example",
            did="did:plc:expert",
            focus="AI engineering",
            identity_confidence="verified",
        )
        self.terms = ["ai", "agent", "inference"]
        self.domains = {"arxiv.org", "github.com"}

    def post(self, key, text, **extra):
        return {
            "post": {
                "uri": f"at://did:plc:expert/app.bsky.feed.post/{key}",
                "author": {"did": "did:plc:expert"},
                "record": {"text": text, "createdAt": "2026-09-20T12:00:00Z"},
                **extra,
            }
        }

    def test_filters_replies_reposts_irrelevant_and_sensitive_posts(self):
        relevant = self.post("one", "A useful AI agent evaluation technique")
        reply = self.post("reply", "AI agent follow-up")
        reply["post"]["record"]["reply"] = {"root": {}, "parent": {}}
        repost = self.post("repost", "AI agent news")
        repost["reason"] = {"$type": "app.bsky.feed.defs#reasonRepost"}
        irrelevant = self.post("garden", "The garden is doing well this year")
        sensitive = self.post("email", "Email ai-team@example.com about this agent")

        items = parse_feed(
            {"feed": [relevant, reply, repost, irrelevant, sensitive]},
            self.account,
            self.terms,
            self.domains,
        )

        self.assertEqual([item.id for item in items], ["bluesky:5d866932b318:one"])
        self.assertEqual(items[0].source_type, "expert-social")
        self.assertEqual(items[0].url, "https://bsky.app/profile/expert.example/post/one")
        self.assertNotIn("likeCount", items[0].to_dict())
        sanitized = sanitize_item(items[0].to_dict())
        self.assertNotIn("metadata", sanitized)
        validate_public_payload({"items": [sanitized]})

    def test_quote_text_and_artifact_link_can_make_a_post_relevant(self):
        quoted = self.post(
            "quote",
            "Worth reading",
            embed={
                "$type": "app.bsky.embed.record#view",
                "record": {"record": {"value": {"text": "New inference benchmark"}}},
            },
        )
        artifact = self.post(
            "artifact",
            "New release",
            embed={"external": {"uri": "https://github.com/example/project"}},
        )

        items = parse_feed(
            {"feed": [quoted, artifact]},
            self.account,
            self.terms,
            self.domains,
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].summary, "New inference benchmark")

    def test_pinned_did_prevents_handle_identity_drift(self):
        post = self.post("wrong-author", "AI agent release")
        post["post"]["author"]["did"] = "did:plc:impostor"

        self.assertEqual(parse_feed({"feed": [post]}, self.account, self.terms, self.domains), [])

    def test_curated_identity_and_gpt_vocabulary_regressions(self):
        config = yaml.safe_load((ROOT / "config/bluesky.yml").read_text(encoding="utf-8"))
        accounts = {account["source_id"]: account for account in config["accounts"]}
        margaret = accounts["bluesky-margaret-mitchell"]
        self.assertEqual(margaret["handle"], "mmitchell.bsky.social")
        self.assertEqual(margaret["did"], "did:plc:3tmaleaxipegsectvamyrkyi")
        self.assertEqual(margaret["identity_confidence"], "verified")
        self.assertIn("gpt", config["include_terms"])

        gpt_post = self.post("gpt", "A useful GPT-4 capability observation")
        items = parse_feed({"feed": [gpt_post]}, self.account, config["include_terms"], set(config["artifact_domains"]))
        self.assertEqual(len(items), 1)


if __name__ == "__main__":
    unittest.main()
