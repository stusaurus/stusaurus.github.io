#!/usr/bin/env python3
"""Read-only crawlability checks; they do not determine Google index coverage."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = "https://stusaurus.github.io"
SITES = {
    "daily-cost-jp": ("", "categories/laundry/", "categories/tissue/", "categories/toilet-paper/"),
    "baby-cost-jp": ("", "diapers/pants/m/", "wipes/", "formula/"),
    "pet-cost-jp": ("", "categories/pet-sheets/", "categories/cat-litter/", "categories/system-toilet-sheets/"),
    "food-cost-jp": ("", "categories/rice/", "categories/pack-rice/", "categories/carbonated-water/"),
    "kyo-bodo-jp": ("", "scenes/two-player/", "scenes/children/", "games/ito/"),
}
OUTPUT = Path("seo-discovery-evidence/report.json")


def parse_locs(xml_data: bytes) -> list[str]:
    tree = ET.fromstring(xml_data)
    tag = tree.tag.split("}")[-1]
    if tag not in ("sitemapindex", "urlset"):
        raise ValueError("Unexpected root element: " + tag)
    return [
        (node.text or "").strip()
        for node in tree.iter()
        if node.tag.split("}")[-1] == "loc"
    ]


class Head(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = []
        self.robots = []
        self.h1_count = 0

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "link" and "canonical" in attr.get("rel", "").lower().split():
            self.canonical.append(attr.get("href", ""))
        if tag == "meta" and attr.get("name", "").lower() == "robots":
            self.robots.append(attr.get("content", ""))


def audit_html(raw: bytes, expected: str) -> list[str]:
    p = Head()
    p.feed(raw.decode("utf-8", errors="replace"))
    problems = []
    if p.canonical != [expected]:
        problems.append("canonical mismatch: " + repr(p.canonical))
    if p.h1_count != 1:
        problems.append("expected one H1, got " + str(p.h1_count))
    if any("noindex" in val.lower() for val in p.robots):
        problems.append("noindex in representative landing page")
    return problems


def fetch(url: str) -> tuple[int, str, bytes]:
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Stusaurus-SEO-Health-Check/1.0 (GitHub Actions; read-only)"},
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.status, response.url, response.read(4_000_000)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"Fetch failed for {url}: {last_error}")


def main() -> int:
    results = []
    failures = []

    def check(name, url, test):
        try:
            status, redirect, raw = fetch(url)
            errors = [] if status == 200 else [f"HTTP {status}"]
            if redirect != url:
                errors.append(f"redirected to {redirect}")
            if not errors:
                errors.extend(test(raw))
        except Exception as exc:
            errors = [f"{type(exc).__name__}: {exc}"]
        results.append({"name": name, "url": url, "errors": errors})
        if errors:
            failures.append({"name": name, "url": url, "errors": errors})
        print(f'{"FAIL" if errors else "PASS"} {name}: {url} {errors}', flush=True)

    root_index = f"{ROOT}/sitemap-index.xml"
    sitemap_urls = {f"{ROOT}/{site}/sitemap.xml" for site in SITES}

    def verify_robots(raw):
        text = raw.decode("utf-8", errors="replace")
        declared = {
            line.strip().split(":", 1)[1].strip()
            for line in text.splitlines()
            if line.strip().lower().startswith("sitemap:")
        }
        return [] if root_index in declared else ["root robots.txt omits root sitemap index"]

    check("shared-robots", f"{ROOT}/robots.txt", verify_robots)

    def verify_index(raw):
        locs = parse_locs(raw)
        return (
            ([] if sitemap_urls.issubset(set(locs)) else ["missing child sitemap: " + repr(sorted(sitemap_urls - set(locs)))])
            + ([] if len(locs) == len(set(locs)) else ["duplicate sitemap index entries"])
        )

    check("shared-sitemap-index", root_index, verify_index)

    for site, paths in SITES.items():
        root_url = f"{ROOT}/{site}/"
        required = {root_url + x for x in paths}
        sitemap_url = root_url + "sitemap.xml"

        def verify_sitemap(raw, required=required, root_url=root_url):
            locs = parse_locs(raw)
            out = []
            if not locs:
                out.append("empty sitemap")
            if len(locs) != len(set(locs)):
                out.append("duplicate sitemap URLs")
            if missing := required - set(locs):
                out.append("missing priority URLs: " + repr(sorted(missing)))
            if illegal := [u for u in locs if not u.startswith(root_url) or urlsplit(u).query or urlsplit(u).fragment]:
                out.append("foreign or parameterized sitemap URLs: " + repr(illegal[:4]))
            return out

        check(f"{site}:sitemap", sitemap_url, verify_sitemap)
        for path in paths:
            u = root_url + path
            check(f"{site}:page:{path or '/'}", u, lambda raw, u=u: audit_html(raw, u))

    OUTPUT.parent.mkdir(exist_ok=True, parents=True)
    OUTPUT.write_text(
        json.dumps(
            {"checks": len(results), "passed": len(results)-len(failures), "failed": len(failures),
             "failures": failures, "results": results,
             "limitations": "This checks public HTTP responses, not actual Googlebot access, Google Search Console sitemap processing or indexing."},
            ensure_ascii=False, indent=2,
        ) + "\n", encoding="utf-8"
    )
    print(f"DISCOVERY_AUDIT checks={len(results)} passed={len(results)-len(failures)} failed={len(failures)}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
