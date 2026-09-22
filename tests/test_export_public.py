import unittest

from pipeline.export_public import PublicDataError, sanitize_item, validate_public_payload


class PublicExportTests(unittest.TestCase):
    def test_allowlists_source_item_fields(self):
        clean = sanitize_item(
            {
                "id": "paper:1",
                "title": "A public paper",
                "url": "https://example.com/paper",
                "summary": "A short original summary.",
                "metadata": {"internal": True},
            }
        )
        self.assertNotIn("metadata", clean)
        self.assertEqual(clean["title"], "A public paper")

    def test_allowlists_only_public_verification_metrics(self):
        clean = sanitize_item(
            {
                "id": "repo:1",
                "source_type": "repository",
                "metadata": {"stars": 12, "forks": 3, "internal": True},
            }
        )
        self.assertEqual(clean["verification"], {"stars": 12, "forks": 3})
        self.assertNotIn("metadata", clean)

    def test_rejects_raw_email_fields(self):
        with self.assertRaises(PublicDataError):
            sanitize_item({"id": "email:1", "raw_body": "private"})

    def test_rejects_email_address_and_gmail_link(self):
        for value in ["person@example.com", "https://mail.google.com/mail/u/0/#all/abc"]:
            with self.subTest(value=value), self.assertRaises(PublicDataError):
                validate_public_payload({"summary": value})


if __name__ == "__main__":
    unittest.main()
