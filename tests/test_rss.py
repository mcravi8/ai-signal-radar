import unittest

from pipeline.collectors.rss import parse


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


if __name__ == "__main__":
    unittest.main()
