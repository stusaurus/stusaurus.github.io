import unittest
from scripts.audit_search_discovery import Head, audit_html, parse_locs


class DiscoveryAuditTests(unittest.TestCase):
    def test_parse_urlset_and_sitemapindex(self):
        xml = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/a/</loc></url></urlset>'
        self.assertEqual(parse_locs(xml), ["https://example.com/a/"])
        xml2 = b'<sitemapindex><sitemap><loc>https://example.com/sitemap.xml</loc></sitemap></sitemapindex>'
        self.assertEqual(parse_locs(xml2), ["https://example.com/sitemap.xml"])

    def test_canonical_and_h1(self):
        url = "https://example.com/a/"
        html = b'<html><head><link rel="canonical" href="https://example.com/a/"></head><body><h1>Test</h1></body></html>'
        self.assertEqual(audit_html(html, url), [])
        self.assertTrue(audit_html(html, "https://example.com/wrong/"))

    def test_noindex_rejected(self):
        html = b'<meta name="robots" content="noindex,follow"><link rel="canonical" href="https://example.com/a/"><h1>Test</h1>'
        self.assertIn("noindex in representative landing page", audit_html(html, "https://example.com/a/"))

    def test_h1_count_rejected(self):
        html = b'<link rel="canonical" href="https://example.com/a/"><h1>One</h1><h1>Two</h1>'
        self.assertIn("expected one H1, got 2", audit_html(html, "https://example.com/a/"))


if __name__ == "__main__":
    unittest.main()
