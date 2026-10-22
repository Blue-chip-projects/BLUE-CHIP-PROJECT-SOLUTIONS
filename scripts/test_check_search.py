"""Regression checks for failures that must prevent search notifications."""
import unittest
from check_search import validate_page, validate_missing, validate_robots, Page, ORIGIN

URL = ORIGIN + "/features"
HTML = '<html><head><title>Features</title><meta name="description" content="Product features"><link rel="canonical" href="' + URL + '"></head><body><h1>Features</h1></body></html>'


class DiscoveryTests(unittest.TestCase):
    def test_indexable_page(self):
        validate_page(URL, 200, {"content-type": "text/html"}, HTML, Page(HTML))

    def test_rejects_login_redirect_homepage_and_noindex(self):
        for html, headers in [
            (HTML.replace(URL, ORIGIN + "/"), {}),
            (HTML.replace("</head>", '<meta name="robots" content="noindex"></head>'), {}),
            (HTML, {"x-robots-tag": "noindex"}),
            ('<title>Sign in</title><h1>Sign in</h1>', {}),
        ]:
            with self.subTest(html=html, headers=headers), self.assertRaises(ValueError):
                validate_page(URL, 200, {"content-type": "text/html", **headers}, html)

    def test_rejects_stale_release(self):
        with self.assertRaises(ValueError):
            validate_page(URL, 200, {"content-type": "text/html"}, HTML.replace('Product features', 'Old description'), Page(HTML))

    def test_unknown_url_must_be_404(self):
        validate_missing(404)
        for status in [200, 302, 403, 500]:
            with self.subTest(status=status), self.assertRaises(ValueError):
                validate_missing(status)

    def test_crawler_specific_block(self):
        robots = 'User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: ' + ORIGIN + '/sitemap.xml\n'
        validate_robots(robots, [URL])
        with self.assertRaises(ValueError):
            validate_robots(robots + '\nUser-agent: OAI-SearchBot\nDisallow: /\n', [URL])


if __name__ == "__main__":
    unittest.main()
