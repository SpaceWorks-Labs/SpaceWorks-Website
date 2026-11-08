"""Regression checks for a complete, reproducible static export with its SEO and GEO files."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import unittest
import xml.etree.ElementTree as ET
from build import build, outputs, PRODUCTS, FAQ, ROOT, URL


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.anchors, self.areas, self.ld, self.meta = [], [], [], [], {}
        self.links, self.h1 = {}, 0
        self._in_ld = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.anchors.append(attrs["href"][1:])
        if "data-area" in attrs:
            self.areas.append(attrs["data-area"])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_ld = True
            self.ld.append("")
        if tag == "meta":
            self.meta[attrs.get("name") or attrs.get("property")] = attrs.get("content")
        if tag == "link":
            self.links[attrs.get("rel")] = attrs.get("href")
        if tag == "h1":
            self.h1 += 1

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False

    def handle_data(self, data):
        if self._in_ld:
            self.ld[-1] += data


def parse(html):
    page = PageParser()
    page.feed(html)
    return page


def ld_types(page):
    return {node["@type"] for block in page.ld for node in json.loads(block)["@graph"]}


class BuildTest(unittest.TestCase):
    def test_complete_page_and_preserved_installer(self):
        html = build()
        self.assertEqual(html, (ROOT / "index.html").read_text(encoding="utf-8"))
        page = parse(html)
        self.assertEqual(len(page.ids), len(set(page.ids)))
        self.assertTrue(set(page.anchors) <= set(page.ids))
        self.assertEqual(set(page.areas), {"inventory", "machines", "events", "bookings", "membership", "payments", "reports", "chat"})
        self.assertEqual(html.count('class="module"'), 9)
        self.assertEqual(html.count('class="feature"'), 12)
        self.assertEqual(html.count('class="app-card"'), len(PRODUCTS))
        self.assertIn('data-copy-text="curl -fsSL https://raw.githubusercontent.com/SpaceWorks-Labs/SpaceWorks/main/install.sh | bash"', html)
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        for font in re.findall(r'url\("(fonts/[^\"]+)"\)', css):
            self.assertTrue((ROOT / font).is_file(), font)
        self.assertNotRegex(html + css, r"IBM|Plex|Archivo")

    def test_every_generated_file_is_committed_and_current(self):
        for name, text in outputs().items():
            self.assertEqual(text, (ROOT / name).read_text(encoding="utf-8"), f"{name} is stale: run python build.py")

    def test_no_links_to_the_old_organisation(self):
        for name, text in outputs().items():
            self.assertNotRegex(text, r"(?i)spaceworks-hq", name)

    def test_pages_have_complete_metadata_and_valid_structured_data(self):
        for name, html in outputs().items():
            if not name.endswith("index.html"):
                continue
            page = parse(html)
            expected = URL + name.removesuffix("index.html")
            self.assertEqual(page.links.get("canonical"), expected, name)
            self.assertEqual(page.meta.get("og:url"), expected, name)
            self.assertTrue(page.meta.get("og:image", "").startswith("https://"), name)
            title = re.search(r"<title>(.*?)</title>", html).group(1)
            self.assertLessEqual(len(title), 65, f"{name}: {title}")
            self.assertTrue(70 <= len(page.meta["description"]) <= 170, f"{name}: {page.meta['description']}")
            self.assertEqual(page.h1, 1, name)
            self.assertEqual(len(page.ids), len(set(page.ids)), name)
            self.assertTrue(set(page.anchors) <= set(page.ids), name)
            self.assertTrue({"Organization", "FAQPage"} <= ld_types(page), name)

    def test_home_describes_platform_apps_and_answers(self):
        page = parse(build())
        self.assertTrue({"WebSite", "SoftwareApplication", "ItemList", "FAQPage"} <= ld_types(page))
        graph = [n for b in page.ld for n in json.loads(b)["@graph"]]
        faq = next(n for n in graph if n["@type"] == "FAQPage")
        self.assertEqual(len(faq["mainEntity"]), len(FAQ))
        listed = next(n for n in graph if n["@type"] == "ItemList")["itemListElement"]
        self.assertEqual([i["url"] for i in listed], [f"{URL}{p['slug']}/" for p in PRODUCTS])

    def test_product_pages_link_their_source_and_breadcrumbs(self):
        files = outputs()
        for p in PRODUCTS:
            html = files[f"{p['slug']}/index.html"]
            self.assertIn("BreadcrumbList", ld_types(parse(html)))
            for repo in p.get("repos") or [p["repo"]]:
                self.assertIn(f"https://github.com/SpaceWorks-Labs/{repo}", html)
            if p.get("install"):
                self.assertIn(f'data-copy-text="{p["install"]}"', html)

    def test_crawler_files(self):
        files = outputs()
        locs = [n.text for n in ET.fromstring(files["sitemap.xml"]).iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertEqual(locs, [URL] + [f"{URL}{p['slug']}/" for p in PRODUCTS])
        self.assertIn(f"Sitemap: {URL}sitemap.xml", files["robots.txt"])
        self.assertTrue(files["llms.txt"].startswith("# Space Works\n\n> "))
        for p in PRODUCTS:
            self.assertIn(f"{URL}{p['slug']}/", files["llms.txt"])
            self.assertIn(p["definition"], files["llms-full.txt"])
        self.assertIn('content="noindex"', files["404.html"])
        host = URL.split("/")[2]
        self.assertEqual("CNAME" in files, not host.endswith(".github.io"))
        self.assertEqual((ROOT / "CNAME").is_file(), "CNAME" in files, "remove a stale CNAME after moving back to github.io")


if __name__ == "__main__":
    unittest.main()
