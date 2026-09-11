"""Recovery planning and paced retry logic with a fake downloader; no network."""

import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import retry_failed_downloads as retry


def target(url, error, status='failed'):
    return dict(url=url, url_id='x', status=status, last_error=error, references=[], registry_entries=[], discoveries=[])


class RetryPlanningTests(unittest.TestCase):
    def test_classification_distinguishes_recoverable_and_skipped_causes(self):
        cases = {
            'HTTPError: HTTP Error 429: Too Many Requests': ('rate-limited', 'retry'),
            'HTTPError: HTTP Error 404: Not Found': ('not-found', 'retry-once'),
            'URLError: <urlopen error [WinError 10061] No connection': ('connection-refused', 'retry'),
            'ValueError: Redirect to unreviewed host: https://cdn.zg.ch/x': ('redirect-unreviewed-host', 'retry'),
            'HTTPError: HTTP Error 302:  - Redirection to url mailto:a@b.ch': ('mailto-redirect', 'skip'),
            'ValueError: Document exceeds 40 MiB; recorded for separate acquisition': ('oversized', 'oversized'),
            'URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] bad>': ('tls-certificate', 'retry-once'),
            'Something new': ('unclassified', 'retry-once'),
        }
        for error, expected in cases.items():
            with self.subTest(error=error):
                self.assertEqual(retry.classify(target('https://www.zh.ch/a', error)), expected)
        self.assertEqual(retry.classify(target('https://www.bfm.admin.ch/a', 'URLError: getaddrinfo failed')),
                         ('dns-failure', 'skip-defunct-host'))
        self.assertEqual(retry.classify(target('https://auth.ag.ch/a', 'HTTPError: HTTP Error 403: Forbidden')),
                         ('forbidden', 'skip-authentication-host'))

    def test_plan_selects_only_failed_targets_and_gates_oversized_on_limit(self):
        state = dict(targets={
            'a': target('https://www.zh.ch/a', 'HTTPError: HTTP Error 429: '),
            'b': target('https://www.zh.ch/b', 'ok', status='saved'),
            'c': target('https://www.sem.admin.ch/big.pdf', 'ValueError: Document exceeds 40 MiB; x'),
            'd': target('https://www.gl.ch/d', 'HTTPError: HTTP Error 302: - Redirection to url mailto:x'),
        })
        selected, skipped = retry.plan(state)
        self.assertEqual([t['url'] for t, _, _ in selected], ['https://www.zh.ch/a'])
        self.assertEqual({s['action'] for s in skipped}, {'skip-oversized', 'skip'})
        selected, skipped = retry.plan(state, oversized_limit=100 * 1024 * 1024)
        self.assertEqual([c for _, c, _ in selected], ['oversized', 'rate-limited'])
        self.assertEqual(len(skipped), 1)


class RetryExecutionTests(unittest.TestCase):
    def setUp(self):
        self.args = SimpleNamespace(host_delay=0, backoff=0, max_attempts=3, max_consecutive_429=2,
                                    oversized_limit=None, dry_run=False)
        self.state = dict(targets={}, audits={}, hosts=['www.zh.ch'])
        self.results, self.lock = [], threading.Lock()

    def run_host(self, items, downloader):
        with patch('retry_failed_downloads.time.sleep'):
            retry.retry_host('www.zh.ch', items, self.state['hosts'], self.args, self.results, self.lock,
                             self.state, download=downloader)

    def test_saved_retry_updates_target_audit_and_discovery(self):
        item = target('https://www.zh.ch/a', 'HTTPError: HTTP Error 429: ')
        audit_result = dict(language_links=[dict(url='https://www.zh.ch/fr/a', advertised_language='fr',
                                                 reason='published-language-link')],
                            topic_links=[], deferred_links=[])
        calls = []

        def downloader(t, hosts, *rest):
            calls.append(rest)
            return dict(status='saved', url=t['url']), audit_result

        self.run_host([(item, 'rate-limited', None)], downloader)
        self.assertEqual(item['status'], 'saved')
        self.assertIsNone(item['last_error'])
        self.assertEqual(self.state['audits']['https://www.zh.ch/a']['basis'], 'live-download-recovery')
        self.assertIn('https://www.zh.ch/fr/a', self.state['targets'])
        self.assertEqual(self.results[0]['status'], 'saved')
        self.assertEqual(self.results[0]['attempts'], 1)
        self.assertEqual(self.results[0]['previous_error'], 'HTTPError: HTTP Error 429: ')
        self.assertEqual(calls, [()])

    def test_repeated_429_pauses_host_and_records_unattempted_targets(self):
        first = target('https://www.zh.ch/a', 'HTTPError: HTTP Error 429: ')
        second = target('https://www.zh.ch/b', 'HTTPError: HTTP Error 429: ')

        def downloader(t, hosts, *rest):
            return dict(status='failed', error='HTTPError: HTTP Error 429: Too Many Requests', url=t['url']), None

        self.run_host([(first, 'rate-limited', None), (second, 'rate-limited', None)], downloader)
        self.assertEqual([r['status'] for r in self.results], ['failed', 'not-attempted-host-paused'])
        self.assertTrue(self.results[0]['host_paused'])
        self.assertEqual(self.results[0]['attempts'], 2)
        self.assertEqual(first['status'], 'failed')
        self.assertEqual(second['status'], 'failed')

    def test_retry_once_respects_single_attempt_and_oversized_limit_is_forwarded(self):
        item = target('https://www.zh.ch/gone', 'HTTPError: HTTP Error 404: Not Found')
        big = target('https://www.zh.ch/big.pdf', 'ValueError: Document exceeds 40 MiB; x')
        self.args.oversized_limit = 123
        seen = []

        def downloader(t, hosts, *rest):
            seen.append((t['url'], rest))
            return dict(status='failed', error='HTTPError: HTTP Error 404: Not Found', url=t['url']), None

        self.run_host([(item, 'not-found', 1), (big, 'oversized', None)], downloader)
        self.assertEqual(seen[0], ('https://www.zh.ch/gone', ()))
        self.assertEqual(self.results[0]['attempts'], 1)
        self.assertEqual(seen[1], ('https://www.zh.ch/big.pdf', (123,)))
        self.assertEqual(self.results[1]['attempts'], 3)

    def test_dry_run_makes_no_request_and_no_change(self):
        item = target('https://www.zh.ch/a', 'HTTPError: HTTP Error 429: ')
        self.args.dry_run = True

        def downloader(*_):
            raise AssertionError('network call in dry run')

        self.run_host([(item, 'rate-limited', None)], downloader)
        self.assertEqual(self.results[0]['status'], 'dry-run')
        self.assertEqual(item['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
