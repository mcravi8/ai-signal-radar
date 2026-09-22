import unittest

from pipeline.collectors.yc import parse_companies, parse_jobs


class YCombinatorCollectorTests(unittest.TestCase):
    def test_parses_public_ai_company_directory_metadata(self):
        page = {
            "props": {
                "companies": [{
                    "id": 42,
                    "slug": "bounded-agent",
                    "name": "Bounded Agent",
                    "batch_name": "s2026",
                    "one_liner": "Agents for finance operations",
                    "long_description": "Runs a governed close workflow.",
                    "tags": ["artificial-intelligence", "fintech"],
                    "ycdc_status": "Active",
                    "team_size": 4,
                    "location": "San Francisco",
                    "github_url": "https://github.com/example/bounded-agent",
                }]
            }
        }
        item = parse_companies(page)[0]
        self.assertEqual(item.id, "yc-company:42")
        self.assertEqual(item.source_type, "company-directory")
        self.assertEqual(item.metadata["batch"], "S2026")
        self.assertNotIn("@", item.summary)

    def test_jobs_are_limited_to_ai_operating_signals(self):
        page = {
            "props": {
                "jobPostings": [
                    {
                        "id": 7,
                        "title": "Machine Learning Engineer",
                        "url": "/jobs/7",
                        "companyName": "Bounded Agent",
                        "companyOneLiner": "Agents for finance operations",
                        "prettyRole": "Engineering",
                        "location": "Remote",
                        "skills": ["LLM evaluation"],
                        "createdAt": "2026-09-22T12:00:00Z",
                    },
                    {
                        "id": 8,
                        "title": "Office Manager",
                        "url": "/jobs/8",
                        "companyName": "Bakery",
                        "companyOneLiner": "Makes bread",
                        "prettyRole": "Operations",
                        "location": "New York",
                        "skills": [],
                        "createdAt": "2026-09-22T12:00:00Z",
                    },
                ]
            }
        }
        items = parse_jobs(page, ["machine learning", "LLM", "agent"])
        self.assertEqual([item.id for item in items], ["yc-job:7"])
        self.assertEqual(items[0].url, "https://www.ycombinator.com/jobs/7")


if __name__ == "__main__":
    unittest.main()
