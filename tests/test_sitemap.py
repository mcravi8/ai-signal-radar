import unittest
from unittest.mock import patch

from pipeline.collectors.sitemap import collect, page_metadata, parse


SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/research/agent-evals</loc><lastmod>2026-09-20T12:00:00Z</lastmod></url>
</urlset>"""

PAGE = b"""<html><head><title>Fallback title</title>
<meta property="og:title" content="Agent evaluations &amp; deployment">
<meta name="description" content="A first-party research announcement.">
</head></html>"""


class SitemapCollectorTests(unittest.TestCase):
    def test_parses_official_sitemap_records(self):
        records, children = parse(SITEMAP)
        self.assertEqual(children, [])
        self.assertEqual(records, [("https://example.com/research/agent-evals", "2026-09-20T12:00:00Z")])

    def test_extracts_public_page_metadata(self):
        title, description = page_metadata(PAGE)
        self.assertEqual(title, "Agent evaluations & deployment")
        self.assertEqual(description, "A first-party research announcement.")

    @patch("pipeline.collectors.sitemap._fetch")
    def test_collect_can_restrict_sitemap_to_issue_pages(self, fetch):
        fetch.side_effect = [
            b'''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url><loc>https://example.com/news/issue-42</loc><lastmod>2026-09-20</lastmod></url>
              <url><loc>https://example.com/news/story-inside-issue</loc><lastmod>2026-09-20</lastmod></url>
              <url><loc>https://example.com/news/tag/agents</loc><lastmod>2026-09-20</lastmod></url>
            </urlset>''',
            b"<html><head><title>Issue 42</title></head></html>",
        ]
        items = collect(
            "newsletter",
            "curated-newsletter",
            "https://example.com/sitemap.xml",
            ["https://example.com/news/"],
            include_patterns=[r"^https://example\.com/news/issue-\d+$"],
        )
        self.assertEqual([item.url for item in items], ["https://example.com/news/issue-42"])


if __name__ == "__main__":
    unittest.main()
