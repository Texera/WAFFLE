import concurrent.futures
from contextlib import closing
import http.client
import secrets
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from server import Allocator, Config, COOKIE, SEQUENCES, make_server
from configure import from_prefilled_link


class StartLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'assignments.sqlite3'
        self.config = Config('https://study.example',
                             'https://docs.google.com/forms/d/e/TEST/viewform',
                             'entry.456')
        self.allocator = Allocator(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_balanced_concurrent_assignments_and_restart(self):
        tokens = [secrets.token_hex(32) for _ in range(80)]
        with concurrent.futures.ThreadPoolExecutor(12) as pool:
            rows = list(pool.map(self.allocator.assign, tokens))
        self.assertEqual(len({r.participant for r in rows}), 80)
        self.assertEqual([sum(r.sequence == s for r in rows) for s in SEQUENCES], [20]*4)
        restarted = Allocator(self.db)
        self.assertEqual(restarted.assign(tokens[0]), rows[0])
        self.assertNotIn(tokens[0].encode(), self.db.read_bytes())

    def test_simultaneous_repeat_has_one_assignment(self):
        token = secrets.token_hex(32)
        with concurrent.futures.ThreadPoolExecutor(12) as pool:
            rows = list(pool.map(self.allocator.assign, [token]*24))
        self.assertEqual(len(set(rows)), 1)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM assignments').fetchone()[0], 1)

    def test_bad_tokens_rejected_without_allocation(self):
        for token in ['', 'short', 'x'*64, 'a'*65, None, '\u00e9'*64]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                self.allocator.assign(token)

    def test_existing_sequence_indices_keep_their_task_and_tool_order(self):
        expected = (
            'Task A on KNIME, then Task B on Texera',
            'Task B on KNIME, then Task A on Texera',
            'Task A on Texera, then Task B on KNIME',
            'Task B on Texera, then Task A on KNIME',
        )
        for index, label in enumerate(expected):
            assigned = Allocator.result((1, index))
            self.assertEqual(assigned.sequence, label)
            fields = parse_qs(urlsplit(self.config.prefill(assigned.sequence)).query)
            self.assertEqual(fields['entry.456'], [label])

    def test_prefill_uses_exact_order_and_fixed_destination(self):
        for sequence in SEQUENCES:
            url = self.config.prefill(sequence)
            parts = urlsplit(url)
            self.assertEqual(parts.netloc, 'docs.google.com')
            self.assertEqual(parse_qs(parts.query), {
                'usp': ['pp_url'], 'entry.456': [sequence]})

    def test_config_rejects_invalid_targets_and_fields(self):
        for kwargs in [dict(origin='http://study.example'),
                       dict(origin='https://study.example/path'),
                       dict(form_url='https://evil.example/forms/d/e/TEST/viewform'),
                       dict(form_url='https://docs.google.com/forms/d/e/TEST/formResponse'),
                       dict(form_url='https://docs.google.com/forms/d/e/TEST/viewform?next=bad'),
                       dict(order_field='123'), dict(order_field='entry.invalid')]:
            args = dict(origin=self.config.origin, form_url=self.config.form_url,
                        order_field=self.config.order_field)
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Config(**args)

    def test_config_from_observed_prefill_link(self):
        link = self.config.prefill(SEQUENCES[0])
        self.assertEqual(from_prefilled_link(link, self.config.origin), self.config)
        for bad in [self.config.form_url, link + '&entry.789=extra',
                    link + '&entry.456=duplicate', self.config.prefill('choose'),
                    link + '&entry.123=TEST-LINK']:
            with self.subTest(link=bad), self.assertRaises(ValueError):
                from_prefilled_link(bad, self.config.origin)

    def test_http_flow_preview_repeat_and_rejections(self):
        server = make_server(('127.0.0.1', 0), self.config, self.allocator)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(method, path, body=None, headers=None):
            connection = http.client.HTTPConnection(*server.server_address, timeout=5)
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            answer = response.status, dict(response.getheaders()), response.read()
            connection.close()
            return answer
        try:
            status, headers, body = request('GET', '/study')
            self.assertEqual(status, 200)
            self.assertIn(b'Opening the study form', body)
            self.assertNotIn(b'participant ID', body)
            self.assertIn("form-action 'self' https://docs.google.com", headers['Content-Security-Policy'])
            # no-referrer makes a browser's HTML form POST send Origin: null.
            self.assertEqual(headers['Referrer-Policy'], 'same-origin')
            self.assertIn('HttpOnly', headers['Set-Cookie'])
            self.assertIn('Secure', headers['Set-Cookie'])
            cookie = headers['Set-Cookie'].split(';', 1)[0]
            with closing(sqlite3.connect(self.db)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM assignments').fetchone()[0], 0)
            self.assertEqual(request('HEAD', '/study')[0], 200)
            good = {'Origin': self.config.origin, 'Cookie': cookie,
                    'Content-Type': 'application/x-www-form-urlencoded'}
            status, headers, _ = request('POST', '/study/start', 'start=1', good)
            self.assertEqual(status, 303)
            destination = headers['Location']
            fields = parse_qs(urlsplit(destination).query)
            self.assertEqual(set(fields), {'usp', 'entry.456'})
            self.assertIn(fields['entry.456'][0], SEQUENCES)
            # Existing Texera/browser cookies must not break our cookie parsing.
            mixed = {'Cookie': 'unrelated={"value":"x"}; ' + cookie}
            self.assertEqual(request('GET', '/study', headers=mixed)[1]['Location'], destination)
            duplicate = dict(good, Cookie=cookie + '; ' + cookie)
            self.assertEqual(request('POST', '/study/start', 'start=1', duplicate)[0], 409)
            malformed = dict(good, Cookie=COOKIE + '=invalid')
            self.assertEqual(request('POST', '/study/start', 'start=1', malformed)[0], 409)
            self.assertEqual(request('POST', '/study/start', 'start=1', good)[1]['Location'], destination)
            self.assertEqual(request('GET', '/study?next=https://evil.example', headers={'Cookie': cookie})[1]['Location'], destination)
            self.assertEqual(request('GET', '/api/config')[0], 404)
            self.assertEqual(request('GET', '/study/start')[0], 404)
            self.assertEqual(request('POST', '/study/start', 'start=1', {'Origin': self.config.origin})[0], 409)
            bad = dict(good, Origin='https://evil.example')
            self.assertEqual(request('POST', '/study/start', 'start=1', bad)[0], 403)
            self.assertEqual(request('POST', '/study/start', 'start=1', dict(good, Origin='null'))[0], 403)
            self.assertEqual(request('POST', '/study/start', 'x'*65, good)[0], 400)
            self.assertEqual(request('POST', '/study/start', 'start=wrong', good)[0], 400)
            with closing(sqlite3.connect(self.db)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM assignments').fetchone()[0], 1)
            status, _, _ = request('GET', '/study', headers={'Cookie': COOKIE+'=bad'})
            self.assertEqual(status, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
