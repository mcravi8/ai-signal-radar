import unittest
from unittest.mock import patch

from pipeline.collectors.html_index import collect, page_metadata, parse_links


INDEX = b'''<html><body>
<a href="/news/issue-43" aria-label="The newest issue"></a>
<a href="https://example.com/news/issue-42">The previous issue</a>
<a href="/about">About</a>
</body></html>'''

PAGE = b'''<html><head>
<meta property="og:title" content="Issue 43: Agent systems">
<meta name="description" content="A weekly research roundup.">
<meta property="article:published_time" content="2026-10-05T12:00:00Z">
</head></html>'''


class HtmlIndexCollectorTests(unittest.TestCase):
    def test_resolves_and_deduplicates_index_links(self):
        self.assertEqual(
            parse_links(INDEX, "https://example.com/news"),
            [
                ("https://example.com/news/issue-43", "The newest issue"),
                ("https://example.com/news/issue-42", "The previous issue"),
                ("https://example.com/about", "About"),
            ],
        )

    def test_extracts_page_metadata_and_publication_time(self):
        self.assertEqual(
            page_metadata(PAGE),
            ("Issue 43: Agent systems", "A weekly research roundup.", "2026-10-05T12:00:00Z"),
        )

    @patch("pipeline.collectors.html_index._fetch")
    def test_collect_restricts_official_index_to_issue_pages(self, fetch):
        fetch.side_effect = [INDEX, PAGE, PAGE]
        items = collect(
            "newsletter",
            "curated-newsletter",
            "https://example.com/news",
            ["https://example.com/news/"],
            include_patterns=[r"^https://example\.com/news/issue-\d+$"],
        )
        self.assertEqual([item.url for item in items], [
            "https://example.com/news/issue-43",
            "https://example.com/news/issue-42",
        ])
        self.assertEqual(items[0].title, "Issue 43: Agent systems")
        self.assertEqual(items[0].published_at, "2026-10-05T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
