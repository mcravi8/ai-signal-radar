import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from pipeline.collectors.rss import _fetch, collect, parse
from pipeline.models import SourceItem


RSS = b"""<?xml version="1.0"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><item>
<title>Agents &amp; markets</title><link>https://example.com/agents</link>
<guid>essay-1</guid><pubDate>Sun, 20 Sep 2026 12:00:00 +0000</pubDate>
<dc:creator>Research Partner</dc:creator><description><![CDATA[<p>An essay about agent infrastructure.</p>]]></description>
</item></channel></rss>"""


class RssCollectorTests(unittest.TestCase):
    def test_normalizes_official_feed_item(self):
        items = parse("essays", "operator-essay", RSS)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.source_id, "essays")
        self.assertEqual(item.title, "Agents & markets")
        self.assertEqual(item.authors, ["Research Partner"])
        self.assertEqual(item.summary, "An essay about agent infrastructure.")
        self.assertTrue(item.published_at.startswith("2026-09-20T12:00:00"))

    def test_accepts_whitespace_before_xml_declaration(self):
        items = parse("essays", "operator-essay", b" \n\t" + RSS)
        self.assertEqual([item.title for item in items], ["Agents & markets"])

    @patch("pipeline.collectors.rss.urllib.request.urlopen")
    def test_retries_forbidden_feed_with_browser_compatible_request(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = RSS
        urlopen.side_effect = [
            urllib.error.HTTPError("https://example.com/feed", 403, "Forbidden", {}, None),
            response,
        ]

        self.assertEqual(_fetch("https://example.com/feed"), RSS)
        retry_request = urlopen.call_args_list[1].args[0]
        self.assertIn("Mozilla/5.0", retry_request.get_header("User-agent"))

    @patch("pipeline.collectors.sitemap.collect")
    @patch("pipeline.collectors.rss._fetch")
    def test_uses_official_sitemap_when_feed_is_unavailable(self, fetch, collect_sitemap):
        fetch.side_effect = urllib.error.HTTPError("https://example.com/feed", 403, "Forbidden", {}, None)
        fallback = SourceItem(
            id="newsletter:fallback",
            source_id="newsletter",
            source_type="expert-newsletter",
            title="Fallback issue",
            url="https://example.com/p/issue-1",
            published_at="2026-10-05",
        )
        collect_sitemap.return_value = [fallback]

        items = collect(
            "newsletter",
            "expert-newsletter",
            "https://example.com/feed",
            fallback_sitemap_url="https://example.com/sitemap.xml",
            fallback_include_prefixes=["https://example.com/p/"],
            fallback_include_patterns=[r"^https://example\.com/p/issue-\d+$"],
        )

        self.assertEqual(items, [fallback])
        collect_sitemap.assert_called_once_with(
            "newsletter",
            "expert-newsletter",
            "https://example.com/sitemap.xml",
            ["https://example.com/p/"],
            30,
            [r"^https://example\.com/p/issue-\d+$"],
        )


if __name__ == "__main__":
    unittest.main()
