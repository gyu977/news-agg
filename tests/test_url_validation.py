"""
Tests for URL validation, redirect unshortening, and health checking.
Verifies url_utils functions and BaseScraper / MailerLiteScraper integration.
"""

import io
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request

import helpers  # noqa: F401 - ensures code/ is on sys.path
from common.base_scraper import BaseScraper
from common.mailerlite_scraper import MailerLiteScraper
from common.url_utils import (
    BROWSER_USER_AGENT,
    _BoundedRedirectHandler,
    clean_tracking_params,
    is_safe_public_url,
    is_tracking_redirect_domain,
    unshorten_url,
    validate_url,
)


class UrlCleanAndTrackingTests(unittest.TestCase):
    def test_clean_tracking_params_empty(self):
        self.assertEqual(clean_tracking_params(""), "")

    def test_clean_tracking_params_removes_marketing_tokens(self):
        url = "https://example.com/post?utm_source=email&utm_campaign=spring&ml_subscriber=12345&keep=me"
        cleaned = clean_tracking_params(url)
        self.assertEqual(cleaned, "https://example.com/post?keep=me")

    def test_clean_tracking_params_preserves_clean_urls(self):
        url = "https://example.com/article?id=99&tab=overview"
        self.assertEqual(clean_tracking_params(url), url)

    def test_is_tracking_redirect_domain(self):
        self.assertTrue(is_tracking_redirect_domain("https://clicks.mlsend.com/link/c/XYZ"))
        self.assertTrue(is_tracking_redirect_domain("https://click.mlsend.com/test"))
        self.assertTrue(is_tracking_redirect_domain("https://bit.ly/3KdQb12"))
        self.assertTrue(is_tracking_redirect_domain("https://t.co/abcxyz"))
        self.assertTrue(is_tracking_redirect_domain("https://link.mail.beehiiv.com/ss/c/xyz"))

        self.assertFalse(is_tracking_redirect_domain("https://martinfowler.com/articles/bliki.html"))
        self.assertFalse(is_tracking_redirect_domain("https://github.com/openai/evals"))
        self.assertFalse(is_tracking_redirect_domain("https://example.com/mlsend.com/fake"))


class SSRFProtectionTests(unittest.TestCase):
    def test_is_safe_public_url(self):
        # Disallow non-HTTP schemes
        self.assertFalse(is_safe_public_url("file:///etc/passwd"))
        self.assertFalse(is_safe_public_url("ftp://example.com/file"))
        self.assertFalse(is_safe_public_url("javascript:alert(1)"))
        self.assertFalse(is_safe_public_url(""))

        # Disallow loopback / local addresses
        self.assertFalse(is_safe_public_url("http://localhost:8080/admin"))
        self.assertFalse(is_safe_public_url("http://127.0.0.1:3000/metrics"))
        self.assertFalse(is_safe_public_url("http://[::1]/status"))
        self.assertFalse(is_safe_public_url("http://server.local/internal"))
        self.assertFalse(is_safe_public_url("http://database.internal:5432"))

        # Disallow private RFC-1918 / RFC-4193 addresses and link-local (cloud metadata)
        self.assertFalse(is_safe_public_url("http://10.0.0.1/secrets"))
        self.assertFalse(is_safe_public_url("http://192.168.1.1/router"))
        self.assertFalse(is_safe_public_url("http://172.16.0.5/api"))
        self.assertFalse(is_safe_public_url("http://169.254.169.254/latest/meta-data/"))

        # Allow legitimate public domains
        self.assertTrue(is_safe_public_url("https://martinfowler.com/articles/bliki.html"))
        self.assertTrue(is_safe_public_url("https://github.com/torvalds/linux"))
        self.assertTrue(is_safe_public_url("http://8.8.8.8/"))

    def test_validate_url_blocks_ssrf(self):
        is_valid, code, msg = validate_url("http://169.254.169.254/latest/meta-data")
        self.assertFalse(is_valid)
        self.assertEqual(code, 0)
        self.assertIn("SSRF protection", msg)

    def test_unshorten_url_blocks_ssrf(self):
        result = unshorten_url("http://127.0.0.1:8000/tracking", force=True)
        self.assertEqual(result, "http://127.0.0.1:8000/tracking")


class UnshortenUrlTests(unittest.TestCase):
    def test_unshorten_skips_non_tracking_by_default(self):
        with patch.object(urllib.request.OpenerDirector, "open") as mock_open:
            result = unshorten_url("https://martinfowler.com/articles/bliki.html")
            mock_open.assert_not_called()
            self.assertEqual(result, "https://martinfowler.com/articles/bliki.html")

    def test_unshorten_follows_redirect_and_cleans_params(self):
        mock_resp = MagicMock()
        mock_resp.geturl.return_value = "https://destination.com/article?utm_medium=email&real=1"
        mock_resp.__enter__.return_value = mock_resp

        with patch.object(urllib.request.OpenerDirector, "open", return_value=mock_resp) as mock_open:
            result = unshorten_url("https://clicks.mlsend.com/link/c/ABC123XYZ", max_hops=3)
            mock_open.assert_called_once()
            # Verify browser User-Agent was passed
            call_arg = mock_open.call_args[0][0]
            self.assertEqual(call_arg.headers["User-agent"], BROWSER_USER_AGENT)
            self.assertEqual(result, "https://destination.com/article?real=1")

    def test_bounded_redirect_handler_enforces_hops(self):
        handler = _BoundedRedirectHandler(max_hops=4)
        self.assertEqual(handler.max_redirections, 4)

    def test_unshorten_handles_location_header_on_httperror(self):
        headers = {"Location": "/redirected-path"}
        err = urllib.error.HTTPError(
            url="https://clicks.mlsend.com/hop2",
            code=302,
            msg="Found",
            hdrs=headers,
            fp=io.BytesIO(b""),
        )

        with patch.object(urllib.request.OpenerDirector, "open", side_effect=err):
            result = unshorten_url("https://clicks.mlsend.com/link/c/XYZ")
            # Should resolve against exc.url rather than clean_original
            self.assertEqual(result, "https://clicks.mlsend.com/redirected-path")
        err.close()

    def test_unshorten_handles_network_error_gracefully(self):
        err = urllib.error.URLError("DNS lookup failed")
        with patch.object(urllib.request.OpenerDirector, "open", side_effect=err), patch("builtins.print"):
            result = unshorten_url("https://clicks.mlsend.com/link/c/XYZ")
            self.assertEqual(result, "https://clicks.mlsend.com/link/c/XYZ")

    def test_unshorten_handles_value_error_gracefully(self):
        with patch.object(urllib.request.OpenerDirector, "open", side_effect=ValueError("bad port")), patch("builtins.print"):
            result = unshorten_url("https://clicks.mlsend.com/link/c/XYZ")
            self.assertEqual(result, "https://clicks.mlsend.com/link/c/XYZ")


class ValidateUrlTests(unittest.TestCase):
    def test_validate_empty_url(self):
        is_valid, code, msg = validate_url("")
        self.assertFalse(is_valid)
        self.assertEqual(code, 0)
        self.assertEqual(msg, "Empty URL")

    def test_validate_200_ok(self):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.geturl.return_value = "https://example.com/ok"
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            is_valid, code, dest = validate_url("https://example.com/ok")
            self.assertTrue(is_valid)
            self.assertEqual(code, 200)
            self.assertEqual(dest, "https://example.com/ok")

    def test_validate_405_fallback_to_get(self):
        # First call (HEAD) raises 405 Method Not Allowed
        err_405 = urllib.error.HTTPError(
            url="https://example.com/no-head",
            code=405,
            msg="Method Not Allowed",
            hdrs={},
            fp=None,
        )
        # Second call (GET fallback) succeeds with 200
        mock_get_resp = MagicMock()
        mock_get_resp.getcode.return_value = 200
        mock_get_resp.geturl.return_value = "https://example.com/no-head"
        mock_get_resp.__enter__.return_value = mock_get_resp

        with patch("urllib.request.urlopen", side_effect=[err_405, mock_get_resp]):
            is_valid, code, dest = validate_url("https://example.com/no-head")
            self.assertTrue(is_valid)
            self.assertEqual(code, 200)
            self.assertEqual(dest, "https://example.com/no-head")

    def test_validate_403_authwall_classified_as_restricted(self):
        err_403 = urllib.error.HTTPError(
            url="https://medium.com/story",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err_403):
            is_valid, code, msg = validate_url("https://medium.com/story")
            self.assertTrue(is_valid)  # Treated as alive/valid host behind anti-bot
            self.assertEqual(code, 403)
            self.assertIn("Restricted/Authwall", msg)

    def test_validate_404_dead_link(self):
        err_404 = urllib.error.HTTPError(
            url="https://example.com/missing",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err_404):
            is_valid, code, msg = validate_url("https://example.com/missing")
            self.assertFalse(is_valid)
            self.assertEqual(code, 404)
            self.assertIn("Dead link", msg)

    def test_validate_dns_error(self):
        err = urllib.error.URLError("Name or service not known")
        with patch("urllib.request.urlopen", side_effect=err):
            is_valid, code, msg = validate_url("https://nonexistent-domain-xyz.com")
            self.assertFalse(is_valid)
            self.assertEqual(code, 0)
            self.assertIn("Connection/DNS", msg)

    def test_validate_value_error(self):
        with patch("urllib.request.urlopen", side_effect=ValueError("invalid URL port")):
            is_valid, code, msg = validate_url("https://example.com:999999")
            self.assertFalse(is_valid)
            self.assertEqual(code, 0)
            self.assertIn("URL Error", msg)


class BaseScraperIntegrationTests(unittest.TestCase):
    def test_base_scraper_methods(self):
        self.assertTrue(BaseScraper.is_tracking_redirect("https://bit.ly/xyz"))
        self.assertFalse(BaseScraper.is_tracking_redirect("https://martinfowler.com"))

        with patch("common.base_scraper._unshorten_url", return_value="https://target.com") as mock_unshorten:
            res = BaseScraper.unshorten_url("https://bit.ly/xyz")
            mock_unshorten.assert_called_once_with("https://bit.ly/xyz", timeout=10, max_hops=5, force=False)
            self.assertEqual(res, "https://target.com")

        with patch("common.base_scraper._validate_url", return_value=(True, 200, "ok")) as mock_val:
            res = BaseScraper.validate_url("https://target.com")
            mock_val.assert_called_once_with("https://target.com", timeout=10)
            self.assertEqual(res, (True, 200, "ok"))


class MailerLiteScraperUnshortenTests(unittest.TestCase):
    def test_parse_issue_html_unshortens_tracking_redirects(self):
        scraper = MailerLiteScraper.__new__(MailerLiteScraper)
        scraper.newsletter_name = "Test NL"
        scraper.article_id_prefix = "tst"
        scraper.blocked_link_terms = ()
        scraper.extract_article_authors = True
        scraper.log_name = "TestMailerLite"
        scraper.definition = None
        html = """
        <html>
          <body>
            <h2><a href="https://clicks.mlsend.com/link/c/ABC999">Awesome Microservices Guide</a></h2>
            <p>A comprehensive walkthrough of bounded contexts and CQRS patterns.</p>
          </body>
        </html>
        """
        target_destination = "https://martinfowler.com/articles/cqrs.html"
        with patch.object(scraper, "unshorten_url", return_value=target_destination) as mock_unshorten:
            articles = scraper.parse_issue_html(
                html=html,
                issue_number=10,
                issue_title="Issue 10",
                issue_link="https://example.com/issues/10",
                date_iso="2026-09-25",
                date_str="Sep 25, 2026",
            )
            mock_unshorten.assert_called_once_with("https://clicks.mlsend.com/link/c/ABC999")
            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].link, target_destination)
            self.assertEqual(articles[0].title, "Awesome Microservices Guide")


if __name__ == "__main__":
    unittest.main()
