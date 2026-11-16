"""Regression checks for the cross-project disclosure page (stdlib only)."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class _Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []
        self.metas = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append(tag)
        if tag == "a":
            self.links.append(values.get("href", ""))
        if tag == "meta":
            self.metas.append(values)


class PrivacyPageTests(unittest.TestCase):
    def test_root_hub_exposes_real_html_link(self):
        parser = _Inspect()
        parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
        self.assertIn("/privacy/", parser.links)

    def test_common_disclosure_covers_current_six_sites(self):
        page = (ROOT / "privacy" / "index.html").read_text(encoding="utf-8")
        parser = _Inspect()
        parser.feed(page)
        for repo in (
            "daily-cost-jp", "baby-cost-jp", "pet-cost-jp",
            "food-cost-jp", "kyo-bodo-jp", "sotojitaku"
        ):
            with self.subTest(repo=repo):
                self.assertIn(f"/{repo}/", parser.links)
        self.assertIn("Google アナリティクス 4", page)
        self.assertIn("Cookie", page)
        self.assertIn("アフィリエイト広告", page)
        self.assertIn("LocalStorage", page)
        self.assertIn("https://policies.google.com/technologies/partner-sites?hl=ja", parser.links)
        self.assertIn("https://tools.google.com/dlpage/gaoptout?hl=ja", parser.links)
        self.assertEqual(parser.tags.count("h1"), 1)
        self.assertEqual(parser.tags.count("main"), 1)
        self.assertTrue(any(m.get("name") == "robots" and m.get("content") == "noindex,follow" for m in parser.metas))


if __name__ == "__main__":
    unittest.main()
