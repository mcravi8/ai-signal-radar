from __future__ import annotations

import io
import unittest
import urllib.error
from unittest.mock import patch

from pipeline.collectors.arxiv import _fetch


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class ArxivCollectorTests(unittest.TestCase):
    @patch("pipeline.collectors.arxiv.time.sleep")
    @patch("pipeline.collectors.arxiv.urllib.request.urlopen")
    def test_fetch_retries_transient_406(self, urlopen, sleep):
        urlopen.side_effect = [
            urllib.error.HTTPError("https://example.test", 406, "Not Acceptable", {}, None),
            _Response(b"<feed />"),
        ]

        self.assertEqual(_fetch("https://example.test"), b"<feed />")
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch("pipeline.collectors.arxiv.time.sleep")
    @patch("pipeline.collectors.arxiv.urllib.request.urlopen")
    def test_fetch_does_not_retry_permanent_error(self, urlopen, sleep):
        urlopen.side_effect = urllib.error.HTTPError("https://example.test", 404, "Not Found", {}, None)

        with self.assertRaises(urllib.error.HTTPError):
            _fetch("https://example.test")
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
