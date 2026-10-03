import json
import tempfile
import unittest
from pathlib import Path

from pipeline.collectors.agentmail import (
    NewsletterDefinition,
    clean_alphasignal_rows,
    collect,
    parse_alphasignal,
    parse_issue,
    read_after,
    write_after,
)
from pipeline.export_public import validate_public_payload


HTML = """
<html><body>
  <a href="https://app.alphasignal.ai/c?uid=private-user&amp;cid=campaignABC123&amp;lid=story1">
    ▸ Claude Code now reads AGENTS.md files for shared project instructions
  </a>
  <a href="https://app.alphasignal.ai/c?uid=private-user&amp;cid=campaignABC123&amp;lid=sponsor1">
    2. Attio agents build your CRM and chase deals from a connected inbox
  </a>
  <p>Presented by Attio</p>
  <a href="https://app.alphasignal.ai/c?uid=private-user&amp;cid=campaignABC123&amp;lid=sponsor1">
    Attio agents build your CRM and chase deals from a connected inbox
  </a>
  <a href="https://app.alphasignal.ai/c?uid=private-user&amp;cid=campaignABC123&amp;lid=read">READ MORE</a>
</body></html>
"""

DEFINITION = NewsletterDefinition(
    source_id="alphasignal",
    source_type="newsletter",
    sender_domains=("alphasignal.ai",),
    parser="alphasignal",
)


class FakeClient:
    def list_messages(self, inbox_id, after=None):
        self.list_call = (inbox_id, after)
        return [
            {
                "message_id": "private-message-id",
                "from": "AlphaSignal <news@alphasignal.ai>",
                "timestamp": "2026-09-28T12:00:00Z",
            },
            {
                "message_id": "unrelated-message-id",
                "from": "Someone <person@example.net>",
                "timestamp": "2026-09-28T13:00:00Z",
            },
        ]

    def get_message(self, inbox_id, message_id):
        return {
            "message_id": message_id,
            "from": "AlphaSignal <news@alphasignal.ai>",
            "timestamp": "2026-09-28T12:00:00Z",
            "subject": "A new issue",
            "html": HTML,
        }


class ExactAddressClient:
    def list_messages(self, inbox_id, after=None):
        return [
            {
                "message_id": "agent-news-message",
                "from": "Adi <adi@agentmail.to>",
                "timestamp": "2026-09-28T14:00:00Z",
            },
            {
                "message_id": "unrelated-agentmail-message",
                "from": "Support <support@agentmail.to>",
                "timestamp": "2026-09-28T15:00:00Z",
            },
        ]

    def get_message(self, inbox_id, message_id):
        return {
            "message_id": message_id,
            "from": "Adi <adi@agentmail.to>",
            "timestamp": "2026-09-28T14:00:00Z",
            "subject": "agentNews issue 1",
            "html": "<p>Issue body remains private.</p>",
        }


class AgentMailCollectorTests(unittest.TestCase):
    def test_alphasignal_cleanup_rejects_spaced_noise_and_collapses_suffix_duplicates(self):
        rows = [
            {
                "id": "old-noise", "source_id": "alphasignal", "source_type": "newsletter",
                "title": "T h i s i s s p a c e d n o i s e", "published_at": "2026-10-01T12:00:00Z",
                "sponsor_status": "sponsored",
            },
            {
                "id": "old-short", "source_id": "alphasignal", "source_type": "newsletter",
                "title": "A useful model release for coding agents", "published_at": "2026-10-01T12:00:00Z",
                "sponsor_status": "editorial",
            },
            {
                "id": "old-long", "source_id": "alphasignal", "source_type": "newsletter",
                "title": "Acme: A useful model release for coding agents", "published_at": "2026-10-01T12:00:00Z",
                "sponsor_status": "sponsored",
            },
            {
                "id": "old-uncertain", "source_id": "alphasignal", "source_type": "newsletter",
                "title": "A standalone item previously caught near an advertisement", "published_at": "2026-10-02T12:00:00Z",
                "sponsor_status": "sponsored",
            },
        ]
        cleaned = clean_alphasignal_rows(rows)
        self.assertEqual(len(cleaned), 2)
        by_title = {item["title"]: item for item in cleaned}
        duplicate = by_title["Acme: A useful model release for coding agents"]
        uncertain = by_title["A standalone item previously caught near an advertisement"]
        self.assertEqual(duplicate["sponsor_status"], "sponsored")
        self.assertEqual(uncertain["sponsor_status"], "unknown")
        self.assertEqual(duplicate["metadata"]["sponsor_basis"], "duplicate-link-title")
        self.assertEqual(
            clean_alphasignal_rows(cleaned)[0]["sponsor_status"],
            "sponsored",
        )
        self.assertNotEqual(duplicate["id"], "old-long")
    def test_generic_issue_extracts_public_links_and_removes_tracking(self):
        definition = NewsletterDefinition(
            source_id="agent-news",
            source_type="operator-newsletter",
            sender_domains=(),
            sender_addresses=("adi@agentmail.to",),
            homepage_url="https://www.agentmail.to/",
            parser="issue",
        )
        items = parse_issue(
            {
                "timestamp": "2026-09-28T14:00:00Z",
                "subject": "AgentNews issue 1",
                "html": """
                    <a href="https://example.com/agent-auth?utm_source=email&amp;ref=private-user">
                      The Great Agent Sign-In Problem
                    </a>
                    <a href="https://example.com/unsubscribe">Unsubscribe</a>
                """,
            },
            definition,
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "The Great Agent Sign-In Problem")
        self.assertEqual(items[0].url, "https://example.com/agent-auth")
        self.assertEqual(items[0].metadata["extraction"], "public-link")

    def test_alphasignal_parser_extracts_editorial_and_sponsored_items(self):
        items = parse_alphasignal(
            {
                "timestamp": "2026-09-28T12:00:00Z",
                "subject": "A new issue",
                "html": HTML,
            },
            DEFINITION,
        )
        self.assertEqual(len(items), 2)
        by_title = {item.title: item for item in items}
        editorial = by_title["Claude Code now reads AGENTS.md files for shared project instructions"]
        sponsored = by_title["Attio agents build your CRM and chase deals from a connected inbox"]
        self.assertEqual(editorial.sponsor_status, "editorial")
        self.assertEqual(sponsored.sponsor_status, "sponsored")
        self.assertEqual(editorial.url, "https://alphasignal.ai/email/campaignABC123")
        self.assertNotIn("uid=", json.dumps([item.to_dict() for item in items]))
        validate_public_payload({"items": [item.to_dict() for item in items]})

    def test_incremental_collection_uses_timestamp_cursor_without_persisting_message_ids(self):
        client = FakeClient()
        result = collect(
            "unused-test-key",
            "radar@agentmail.to",
            [DEFINITION],
            after="2026-09-21T00:00:00Z",
            client=client,
        )
        self.assertEqual(client.list_call, ("radar@agentmail.to", "2026-08-17T00:00:00.000Z"))
        self.assertEqual(result.messages_seen, 2)
        self.assertEqual(result.messages_matched, 1)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.next_after, "2026-09-28T13:00:00Z")

    def test_incremental_cursor_is_normalized_to_agentmail_utc_format(self):
        client = FakeClient()
        collect(
            "unused-test-key",
            "radar@agentmail.to",
            [DEFINITION],
            after="2026-09-22T15:32:33.000+00:00",
            client=client,
        )
        self.assertEqual(client.list_call, ("radar@agentmail.to", "2026-08-18T15:32:33.000Z"))

    def test_exact_sender_address_does_not_trust_the_shared_domain(self):
        definition = NewsletterDefinition(
            source_id="agent-news",
            source_type="operator-newsletter",
            sender_domains=(),
            sender_addresses=("adi@agentmail.to",),
            homepage_url="https://www.agentmail.to/",
            parser="issue",
        )
        result = collect(
            "unused-test-key",
            "radar@agentmail.to",
            [definition],
            client=ExactAddressClient(),
        )
        self.assertEqual(result.messages_seen, 2)
        self.assertEqual(result.messages_matched, 1)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].source_id, "agent-news")
        self.assertEqual(result.items[0].url, "https://www.agentmail.to/")

    def test_cursor_contains_only_public_safe_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cursor.json"
            write_after(path, "2026-09-28T13:00:00Z")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(read_after(path), "2026-09-28T13:00:00Z")
            self.assertEqual(set(payload), {"after", "updated_at", "note"})
            validate_public_payload(payload)


if __name__ == "__main__":
    unittest.main()
