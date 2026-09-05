from __future__ import annotations

import sys
import unittest
from email.message import Message
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from swisstip.ingestion import CrawlLimits, SafeCrawler, SourceDefinition  # noqa: E402


PUBLIC_DNS_RESULT = [(2, 1, 6, "", ("93.184.216.34", 443))]


def public_resolver(*_args, **_kwargs):
    return PUBLIC_DNS_RESULT


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: bytes = b"",
        *,
        content_type: str = "text/html; charset=utf-8",
        headers: dict[str, str] | None = None,
        publish_length: bool = True,
    ) -> None:
        self._status = status
        self._body = body
        self._offset = 0
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if publish_length:
            self.headers["Content-Length"] = str(len(body))
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def getcode(self) -> int:
        return self._status

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._body) - self._offset
        start = self._offset
        self._offset = min(len(self._body), self._offset + size)
        return self._body[start : self._offset]

    def close(self) -> None:
        pass


class FakeOpener:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.requested: list[str] = []

    def open(self, request, timeout=None):  # noqa: ANN001, ARG002
        self.requested.append(request.full_url)
        response = self.responses.get(request.full_url)
        if response is None:
            raise OSError(f"unexpected request: {request.full_url}")
        return response


def crawler_for(
    responses: dict[str, FakeResponse],
    *,
    max_depth: int = 1,
    max_pages: int = 10,
    max_response_bytes: int = 10_000,
) -> tuple[SafeCrawler, FakeOpener]:
    opener = FakeOpener(responses)
    source = SourceDefinition(
        source_id="test-source",
        start_url="https://official.example/allowed/start",
        allowed_path_prefixes=("/allowed/",),
    )
    limits = CrawlLimits(
        max_depth=max_depth,
        max_pages=max_pages,
        max_requests=20,
        max_total_bytes=100_000,
        max_response_bytes=max_response_bytes,
        max_duration_seconds=10,
        request_timeout_seconds=1,
        delay_seconds=0,
        max_redirects=2,
        max_links_per_page=20,
        max_queued_urls=20,
        max_failures=3,
    )
    crawler = SafeCrawler(
        source,
        limits,
        opener=opener,
        resolver=public_resolver,
    )
    return crawler, opener


class SafeCrawlerTests(unittest.TestCase):
    def test_depth_scope_queries_and_robots_are_enforced(self) -> None:
        robots = b"User-agent: *\nDisallow: /allowed/blocked\n"
        start = b"""
            <html><title>Start</title><body>
            <a href="/allowed/level-1">one</a>
            <a href="/allowed/blocked">blocked</a>
            <a href="/outside">outside</a>
            <a href="/allowed/search?q=trap">query</a>
            <a href="https://other.example/page">external</a>
            </body></html>
        """
        level_1 = b'<html><a href="/allowed/level-2">too deep</a></html>'
        crawler, opener = crawler_for(
            {
                "https://official.example/robots.txt": FakeResponse(
                    200, robots, content_type="text/plain"
                ),
                "https://official.example/allowed/start": FakeResponse(200, start),
                "https://official.example/allowed/level-1": FakeResponse(200, level_1),
            }
        )

        report = crawler.crawl()

        self.assertEqual(report.stop_reason, "frontier-exhausted")
        self.assertEqual(report.robots_status, "loaded")
        self.assertEqual(len(report.pages), 2)
        self.assertEqual(report.requests_sent, 3)
        self.assertEqual(report.pages[0].title, "Start")
        self.assertNotIn("https://official.example/allowed/blocked", opener.requested)
        self.assertNotIn("https://official.example/allowed/level-2", opener.requested)
        reasons = {item.reason for item in report.skipped}
        self.assertIn("out-of-scope", reasons)
        self.assertIn("query-string-disabled", reasons)
        self.assertIn("robots-disallowed", reasons)

    def test_page_budget_stops_before_an_extra_request(self) -> None:
        crawler, opener = crawler_for(
            {
                "https://official.example/robots.txt": FakeResponse(
                    200, b"User-agent: *\nAllow: /\n", content_type="text/plain"
                ),
                "https://official.example/allowed/start": FakeResponse(
                    200, b'<a href="/allowed/next">next</a>'
                ),
            },
            max_pages=1,
        )

        report = crawler.crawl()

        self.assertEqual(report.stop_reason, "page-limit")
        self.assertEqual(report.requests_sent, 2)
        self.assertEqual(len(opener.requested), 2)

    def test_cross_host_redirect_is_not_followed(self) -> None:
        crawler, opener = crawler_for(
            {
                "https://official.example/robots.txt": FakeResponse(
                    200, b"User-agent: *\nAllow: /\n", content_type="text/plain"
                ),
                "https://official.example/allowed/start": FakeResponse(
                    302,
                    headers={"Location": "https://other.example/escape"},
                ),
            }
        )

        report = crawler.crawl()

        self.assertEqual(len(report.pages), 0)
        self.assertEqual(report.requests_sent, 2)
        self.assertEqual(len(opener.requested), 2)
        self.assertTrue(
            any(item.reason.startswith("redirect-out-of-scope") for item in report.skipped)
        )

    def test_stream_without_content_length_stops_at_response_limit(self) -> None:
        crawler, _ = crawler_for(
            {
                "https://official.example/robots.txt": FakeResponse(
                    200, b"User-agent: *\nAllow: /\n", content_type="text/plain"
                ),
                "https://official.example/allowed/start": FakeResponse(
                    200,
                    b"x" * 100,
                    publish_length=False,
                ),
            },
            max_response_bytes=25,
        )

        report = crawler.crawl()

        self.assertEqual(report.pages[0].outcome, "response-limit-reached")
        self.assertEqual(report.pages[0].bytes_downloaded, 25)

    def test_non_html_body_is_not_downloaded(self) -> None:
        crawler, _ = crawler_for(
            {
                "https://official.example/robots.txt": FakeResponse(
                    200, b"User-agent: *\nAllow: /\n", content_type="text/plain"
                ),
                "https://official.example/allowed/start": FakeResponse(
                    200, b"%PDF large payload", content_type="application/pdf"
                ),
            }
        )

        report = crawler.crawl()

        self.assertEqual(report.pages[0].outcome, "content-type-skipped")
        self.assertEqual(report.pages[0].bytes_downloaded, 0)

    def test_private_dns_target_is_rejected_before_any_request(self) -> None:
        crawler, opener = crawler_for({})
        crawler._resolver = lambda *_args, **_kwargs: [  # noqa: SLF001
            (2, 1, 6, "", ("127.0.0.1", 443))
        ]

        report = crawler.crawl()

        self.assertEqual(report.stop_reason, "unsafe-start-url")
        self.assertEqual(report.requests_sent, 0)
        self.assertEqual(opener.requested, [])

    def test_robots_failure_is_fail_closed(self) -> None:
        crawler, opener = crawler_for({})

        report = crawler.crawl()

        self.assertEqual(report.stop_reason, "robots-unavailable")
        self.assertEqual(report.robots_status, "unavailable-fail-closed")
        self.assertEqual(report.requests_sent, 1)
        self.assertEqual(
            opener.requested, ["https://official.example/robots.txt"]
        )


if __name__ == "__main__":
    unittest.main()
