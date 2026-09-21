import unittest

from pipeline.collectors.sitemap import page_metadata, parse


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


if __name__ == "__main__":
    unittest.main()
