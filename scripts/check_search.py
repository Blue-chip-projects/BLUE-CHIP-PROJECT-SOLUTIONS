"""Validate public discovery locally and, optionally, on the deployed site.

Standard library only. All live requests are read-only. No enquiries are sent.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://jenasaro.com"
KEY_FILE = "5ba54a09c02a245117bd2c602394e6c855172bfbd0034ad7.txt"
CRAWLERS = ("Googlebot", "bingbot", "OAI-SearchBot", "PerplexityBot")


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.meta = {}
        self.links = []
        self.ids = set()
        self.title = ""
        self.h1 = ""
        self.in_title = self.in_h1 = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href", ""))
        if tag == "meta":
            self.meta[attrs.get("name", attrs.get("property", "")).lower()] = attrs.get("content", "")
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.in_h1 = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "h1":
            self.in_h1 = False

    def handle_data(self, text):
        if self.in_title:
            self.title += text
        if self.in_h1:
            self.h1 += text


def require(condition, message):
    if not condition:
        raise ValueError(message)


def page_file(url):
    path = urllib.parse.urlsplit(url).path
    return ROOT / (path.lstrip("/") + ".html" if path != "/" else "index.html")


def sitemap_urls(xml):
    root = ET.fromstring(xml)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    require(root.tag == "{" + ns["s"] + "}urlset", "Invalid sitemap root")
    urls = []
    for item in root.findall("s:url", ns):
        url = (item.findtext("s:loc", namespaces=ns) or "").strip()
        parsed = urllib.parse.urlsplit(url)
        require(parsed.scheme == "https" and parsed.netloc == "jenasaro.com", f"Unexpected sitemap host: {url}")
        require(not parsed.query and not parsed.fragment, f"Noncanonical sitemap URL: {url}")
        require(url not in urls, f"Duplicate sitemap URL: {url}")
        modified = item.findtext("s:lastmod", namespaces=ns)
        if modified:
            require(date.fromisoformat(modified[:10]) <= date.today(), f"Future sitemap date: {url}")
        urls.append(url)
    require(bool(urls), "Sitemap is empty")
    return urls


def validate_page(url, status, headers, html, expected=None):
    require(status == 200, f"{url}: HTTP {status}, expected 200")
    require("text/html" in headers.get("content-type", "").lower(), f"{url}: not HTML")
    require("noindex" not in headers.get("x-robots-tag", "").lower(), f"{url}: HTTP noindex")
    page = Page(html)
    require(page.canonicals == [url], f"{url}: wrong canonical {page.canonicals}")
    require(bool(page.title.strip()) and bool(page.h1.strip()), f"{url}: missing title or heading")
    for agent in ("robots", "googlebot", "bingbot"):
        require(not re.search(r"\b(noindex|none)\b", page.meta.get(agent, "").lower()), f"{url}: {agent} prevents indexing")
    require(bool(page.meta.get("description", "").strip()), f"{url}: missing description")
    if expected:
        require((page.title, page.h1, page.meta.get("description")) ==
                (expected.title, expected.h1, expected.meta.get("description")), f"{url}: deployed content is stale")
    for block in re.findall(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>', html, re.S | re.I):
        json.loads(block)
    return page


def validate_robots(text, urls):
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(text.splitlines())
    # robotparser uses first-match order; the site's literal rules need the
    # longest matching path first, with Allow winning ties (RFC 9309).
    for entry in robots.entries + ([robots.default_entry] if robots.default_entry else []):
        entry.rulelines.sort(key=lambda rule: (len(rule.path), rule.allowance), reverse=True)
    require(ORIGIN + "/sitemap.xml" in (robots.site_maps() or []), "robots.txt is missing the sitemap")
    for agent in CRAWLERS:
        for url in urls:
            require(robots.can_fetch(agent, url), f"robots.txt blocks {agent}: {url}")
        require(not robots.can_fetch(agent, ORIGIN + "/api/interest"), f"robots.txt should exclude /api/ for {agent}")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Jenasaro-Search-Check/1.0", "Cache-Control": "no-cache"})
    try:
        response = urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read().decode("utf-8", errors="replace"), response.url


def validate_missing(status):
    require(status == 404, f"Unknown URL returns HTTP {status}; expected a real 404, not the homepage")


def check_local():
    urls = sitemap_urls((ROOT / "sitemap.xml").read_text())
    pages = {}
    for url in urls:
        pages[url] = validate_page(url, 200, {"content-type": "text/html"}, page_file(url).read_text())
    validate_robots((ROOT / "robots.txt").read_text(), urls)
    error_page = Page((ROOT / "404.html").read_text())
    require("noindex" in error_page.meta.get("robots", ""), "404 page must be noindex")
    require(not error_page.canonicals, "404 page must not canonicalize to the homepage")
    require(bool(pages[ORIGIN + "/"].meta.get("google-site-verification")), "Preserve Google ownership verification")
    # Confirm that indexed pages can be reached through real HTML links.
    visited, pending = set(), [ORIGIN + "/"]
    while pending:
        url = pending.pop()
        if url in visited or url not in pages:
            continue
        visited.add(url)
        for href in pages[url].links:
            target = urllib.parse.urlsplit(urllib.parse.urljoin(url, href))
            if target.netloc != "jenasaro.com":
                continue
            clean = urllib.parse.urlunsplit((target.scheme, target.netloc, target.path, "", ""))
            if clean in pages:
                if target.fragment:
                    require(target.fragment in pages[clean].ids, f"Broken anchor: {url} -> {href}")
                pending.append(clean)
            else:
                local = ROOT / target.path.lstrip("/")
                require(local.is_file() or page_file(clean).is_file(), f"Broken local link: {url} -> {href}")
    require(set(urls) == visited, f"Orphan sitemap pages: {set(urls) - visited}")
    print(f"PASS: {len(urls)} public pages, canonicals, metadata, structured data, links, robots and 404 configuration")
    return urls, pages


def check_live(base, urls, pages):
    base = base.rstrip("/")
    status, headers, xml, _ = fetch(base + "/sitemap.xml")
    require(status == 200 and "xml" in headers.get("content-type", ""), "Live sitemap is not valid XML with HTTP 200")
    require(sitemap_urls(xml) == urls, "Live sitemap has not caught up with this release")
    status, _, robots, _ = fetch(base + "/robots.txt")
    require(status == 200, "Live robots.txt is unavailable")
    validate_robots(robots, urls)
    def check(url):
        status, headers, html, final = fetch(base + urllib.parse.urlsplit(url).path)
        require(urllib.parse.urlsplit(final).path == urllib.parse.urlsplit(url).path, f"Unexpected redirect: {url} -> {final}")
        validate_page(url, status, headers, html, pages[url])
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(check, urls))
    status, _, key, _ = fetch(base + "/" + KEY_FILE)
    require(status == 200 and key.strip() == (ROOT / KEY_FILE).read_text().strip(), "Live IndexNow verification key mismatch")
    status, _, _, _ = fetch(base + "/__jenasaro_search_check_missing__")
    validate_missing(status)
    print(f"PASS: live sitemap, {len(urls)} pages, search permissions, IndexNow key and genuine 404 at {base}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--base-url", default=ORIGIN)
    args = parser.parse_args()
    try:
        urls, pages = check_local()
        if args.live:
            check_live(args.base_url, urls, pages)
    except (ValueError, OSError, ET.ParseError) as error:
        parser.exit(1, f"FAIL: {error}\n")
