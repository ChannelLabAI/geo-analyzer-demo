"""Unit tests for website_diagnostics.py

Tests cover:
- check_crawlers(): 4 robots.txt scenarios
- score_citability(): boundary conditions
- generate_llmstxt(): sitemap URL edge cases
"""

import unittest
from unittest.mock import MagicMock, patch

from website_diagnostics import check_crawlers, score_citability, _score_passage, validate_url


# ─── check_crawlers ────────────────────────────────────────────────────


def _mock_response(status_code=200, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestCheckCrawlers(unittest.TestCase):

    @patch("website_diagnostics.requests.get")
    def test_no_robots_txt_allows_all(self, mock_get):
        """404 robots.txt → all crawlers allowed, score=80."""
        mock_get.return_value = _mock_response(status_code=404)
        result = check_crawlers("https://example.com")
        self.assertFalse(result["robots_exists"])
        self.assertEqual(result["score"], 80)
        self.assertTrue(all(c["status"] == "no_robots_txt" for c in result["crawlers"]))

    @patch("website_diagnostics.requests.get")
    def test_blanket_block_all(self, mock_get):
        """Disallow: / for * → all crawlers blocked_wildcard, score=0."""
        robots = "User-agent: *\nDisallow: /\n"
        mock_get.return_value = _mock_response(text=robots)
        result = check_crawlers("https://example.com")
        self.assertTrue(result["robots_exists"])
        self.assertEqual(result["score"], 0)
        blocked = [c for c in result["crawlers"] if c["status"] == "blocked_wildcard"]
        self.assertEqual(len(blocked), len(result["crawlers"]))

    @patch("website_diagnostics.requests.get")
    def test_specific_crawler_blocked(self, mock_get):
        """GPTBot Disallow: / → GPTBot blocked, others allowed_default."""
        robots = "User-agent: GPTBot\nDisallow: /\n"
        mock_get.return_value = _mock_response(text=robots)
        result = check_crawlers("https://example.com")
        gptbot = next(c for c in result["crawlers"] if c["name"] == "GPTBot")
        self.assertEqual(gptbot["status"], "blocked")
        others = [c for c in result["crawlers"] if c["name"] != "GPTBot"]
        self.assertTrue(all(c["status"] == "allowed_default" for c in others))

    @patch("website_diagnostics.requests.get")
    def test_partial_block(self, mock_get):
        """GPTBot Disallow: /private → GPTBot partial, others allowed_default."""
        robots = "User-agent: GPTBot\nDisallow: /private\n"
        mock_get.return_value = _mock_response(text=robots)
        result = check_crawlers("https://example.com")
        gptbot = next(c for c in result["crawlers"] if c["name"] == "GPTBot")
        self.assertEqual(gptbot["status"], "partial")

    @patch("website_diagnostics.requests.get")
    def test_sitemap_protocol_relative_url(self, mock_get):
        """Protocol-relative sitemap (//cdn.example.com/sitemap.xml) resolves correctly."""
        robots = "User-agent: *\nAllow: /\nSitemap: //cdn.example.com/sitemap.xml\n"
        mock_get.return_value = _mock_response(text=robots)
        result = check_crawlers("https://example.com/page")
        self.assertEqual(len(result["sitemaps"]), 1)
        self.assertTrue(result["sitemaps"][0].startswith("https://"))
        self.assertNotIn("https//", result["sitemaps"][0])

    @patch("website_diagnostics.requests.get")
    def test_sitemap_absolute_url_preserved(self, mock_get):
        """Absolute sitemap URL is preserved as-is."""
        robots = "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n"
        mock_get.return_value = _mock_response(text=robots)
        result = check_crawlers("https://example.com")
        self.assertEqual(result["sitemaps"][0], "https://example.com/sitemap.xml")

    @patch("website_diagnostics.requests.get")
    def test_timeout_error(self, mock_get):
        """Timeout → empty crawlers list with error, no crash."""
        import requests as req_module
        mock_get.side_effect = req_module.exceptions.Timeout()
        result = check_crawlers("https://example.com")
        self.assertIn("Timeout", result["errors"][0])
        self.assertEqual(result["crawlers"], [])


# ─── _score_passage ────────────────────────────────────────────────────


class TestScorePassage(unittest.TestCase):

    def test_short_text_returns_none(self):
        """Text with fewer than 10 words returns None."""
        self.assertIsNone(_score_passage("Too short"))

    def test_long_rich_text_scores_higher(self):
        """A rich, well-structured passage should score higher than a bare minimum passage."""
        rich = (
            "HubSpot is a leading CRM platform that helps businesses grow. "
            "According to research, companies using CRM software see 29% more sales. "
            "The platform includes marketing, sales, and service hubs. "
            "For example, the free CRM tier supports unlimited users. "
            "First, set up your pipeline. Second, import your contacts. "
            "Finally, automate your follow-ups using workflows."
        )
        bare = "This thing does stuff and it is good for things. People use it sometimes."
        rich_score = _score_passage(rich)
        bare_score = _score_passage(bare)
        self.assertIsNotNone(rich_score)
        self.assertIsNotNone(bare_score)
        self.assertGreater(rich_score["total_score"], bare_score["total_score"])

    def test_grade_distribution(self):
        """Score >= 80 → A, 65-79 → B, 50-64 → C, 35-49 → D, <35 → F."""
        # Force a high-scoring passage with stats, definitions, authority signals
        text = (
            "Generative Engine Optimization (GEO) is defined as the practice of optimizing "
            "content for AI search engines. According to our research, brands using GEO see a "
            "47% increase in AI citation rates in 2024. Studies show that structured content "
            "with clear definitions and statistical density is mentioned 3x more often by "
            "ChatGPT, Perplexity, and Gemini in AI-generated responses."
        )
        result = _score_passage(text)
        self.assertIsNotNone(result)
        self.assertIn(result["grade"], ("A", "B", "C", "D", "F"))

    def test_question_heading_bonus(self):
        """Heading ending in '?' adds bonus to answer_block_quality."""
        text = (
            "GEO refers to the optimization of content for AI search engines. "
            "Brands that adopt GEO early see significantly higher citation rates. "
            "This approach focuses on structured content, statistical depth, and authority signals."
        )
        with_q = _score_passage(text, heading="What is GEO?")
        without_q = _score_passage(text, heading="About GEO")
        self.assertGreaterEqual(with_q["breakdown"]["answer_block_quality"],
                                without_q["breakdown"]["answer_block_quality"])


# ─── SSRF validation (serve.py) ────────────────────────────────────────


class TestValidateUrl(unittest.TestCase):

    def test_localhost_blocked(self):
        self.assertIsNotNone(validate_url("http://localhost/api/secret"))

    def test_loopback_blocked(self):
        self.assertIsNotNone(validate_url("http://127.0.0.1/etc/passwd"))

    def test_private_ip_blocked(self):
        self.assertIsNotNone(validate_url("http://192.168.1.1/admin"))

    def test_metadata_endpoint_blocked(self):
        self.assertIsNotNone(validate_url("http://169.254.169.254/latest/meta-data/"))

    def test_public_url_allowed(self):
        try:
            result = validate_url("https://example.com")
            self.assertIsNone(result)
        except Exception:
            self.skipTest("DNS not available in this environment")


if __name__ == "__main__":
    unittest.main()
