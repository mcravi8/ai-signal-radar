import json
import tempfile
import unittest
from pathlib import Path

from pipeline.collectors.agentmail import (
    NewsletterDefinition,
    collect,
    parse_alphasignal,
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


class AgentMailCollectorTests(unittest.TestCase):
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
        self.assertEqual(client.list_call, ("radar@agentmail.to", "2026-09-20T23:55:00+00:00"))
        self.assertEqual(result.messages_seen, 2)
        self.assertEqual(result.messages_matched, 1)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.next_after, "2026-09-28T13:00:00Z")

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
