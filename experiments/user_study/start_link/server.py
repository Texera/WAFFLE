"""One study URL, durable balanced assignment, then Google Forms prefill.

Python 3.12 standard library only. Run behind an HTTPS reverse proxy.
No workflow execution, Form submission, or access to Texera credentials.
"""
import argparse
from contextlib import closing, contextmanager
import hashlib
import html
import http.server
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

COOKIE = '__Host-waffle-study'
SEQUENCES = (
    'Task A on KNIME, then Task B on Texera',
    'Task B on KNIME, then Task A on Texera',
    'Task A on Texera, then Task B on KNIME',
    'Task B on Texera, then Task A on KNIME',
)


def valid_token(token):
    return isinstance(token, str) and re.fullmatch('[a-f0-9]{64}', token) is not None


@dataclass(frozen=True)
class Assignment:
    participant: str
    sequence: str


@dataclass(frozen=True)
class Config:
    origin: str
    form_url: str
    order_field: str

    def __post_init__(self):
        origin = urlsplit(self.origin)
        if (origin.scheme != 'https' or not origin.hostname or origin.path or
                origin.query or origin.fragment or origin.username or origin.password):
            raise ValueError('origin must be an HTTPS origin without a path')
        if not re.fullmatch(r'https://docs\.google\.com/forms/d/e/[A-Za-z0-9_-]+/viewform', self.form_url):
            raise ValueError('form_url must be a Google Forms respondent URL without a query')
        if not re.fullmatch(r'entry\.[0-9]+', self.order_field):
            raise ValueError('Use the sequence entry field from Get pre-filled link')

    def prefill(self, sequence):
        return self.form_url + '?' + urlencode({
            'usp': 'pp_url', self.order_field: sequence})


class Allocator:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT NOT NULL UNIQUE,
                sequence INTEGER NOT NULL CHECK(sequence BETWEEN 0 AND 3),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )''')
        os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            with db:
                yield db

    @staticmethod
    def key(token):
        if not valid_token(token):
            raise ValueError('Invalid browser token')
        return hashlib.sha256(token.encode('ascii')).hexdigest()

    @staticmethod
    def result(row):
        return Assignment(f'W{row[0]:04d}', SEQUENCES[row[1]]) if row else None

    def find(self, token):
        key = self.key(token)
        with self.connect() as db:
            return self.result(db.execute(
                'SELECT id,sequence FROM assignments WHERE token_hash=?', (key,)).fetchone())

    def assign(self, token):
        key = self.key(token)
        with self.connect() as db:
            # Serialize find/count/insert so simultaneous visits stay balanced.
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT id,sequence FROM assignments WHERE token_hash=?', (key,)).fetchone()
            if old:
                return self.result(old)
            counts = dict(db.execute('SELECT sequence,count(*) FROM assignments GROUP BY sequence'))
            minimum = min(counts.get(s, 0) for s in range(4))
            sequence = secrets.choice([s for s in range(4) if counts.get(s, 0) == minimum])
            cursor = db.execute('INSERT INTO assignments(token_hash,sequence) VALUES(?,?)', (key, sequence))
            return self.result((cursor.lastrowid, sequence))


def make_server(address, config, allocator):
    class Handler(http.server.BaseHTTPRequestHandler):
        # Never write cookies, IDs or Form URLs to an access log.
        def log_message(self, *_):
            pass

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def respond(self, status, body='', headers=None, nonce=None):
            data = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            # Keep Origin on our same-origin form POST, but omit referrers to Google.
            self.send_header('Referrer-Policy', 'same-origin')
            self.send_header('X-Content-Type-Options', 'nosniff')
            csp = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://docs.google.com; frame-ancestors 'none'; base-uri 'none'"
            if nonce:
                csp += "; script-src 'nonce-" + nonce + "'"
            self.send_header('Content-Security-Policy', csp)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        def token(self):
            # Parse only our fixed-format token. An unrelated JSON-valued cookie
            # can make SimpleCookie silently discard the entire request header.
            values = []
            for header in self.headers.get_all('Cookie', []):
                for pair in header.split(';'):
                    name, separator, value = pair.strip().partition('=')
                    if name == COOKIE and separator:
                        values.append(value)
            return values[0] if len(values) == 1 and valid_token(values[0]) else None

        def redirect(self, assignment):
            self.respond(303, headers={'Location': config.prefill(
                assignment.sequence)})

        def do_HEAD(self):
            self.respond(200 if urlsplit(self.path).path in ('/study', '/study/') else 404)

        def do_GET(self):
            if urlsplit(self.path).path not in ('/study', '/study/'):
                self.respond(404, 'Not found')
                return
            token = self.token()
            try:
                old = allocator.find(token) if token else None
                if old:
                    self.redirect(old)
                    return
            except sqlite3.Error:
                self.respond(503, 'Please try again shortly.')
                return
            token = token or secrets.token_hex(32)
            nonce = secrets.token_urlsafe(18)
            body = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WAFFLE study</title><style>body{font:18px/1.5 system-ui;max-width:40rem;margin:12vh auto;padding:1.5rem}button{font:inherit;padding:.6rem 1.2rem}</style>
<h1>Opening the study form…</h1>
<p>Your task order will be filled in automatically.</p>
<p>Use this browser if you return, so your assignment stays the same.</p>
<form method="post" action="/study/start" id="start"><input type="hidden" name="start" value="1"><button>Continue to the form</button></form>
<noscript><p>Select Continue to open the form.</p></noscript>
<script nonce="''' + html.escape(nonce, quote=True) + '''">document.getElementById('start').submit();</script></html>'''
            self.respond(200, body, {'Set-Cookie':
                f'{COOKIE}={token}; Path=/; Max-Age=7776000; Secure; HttpOnly; SameSite=Lax'}, nonce)

        def do_POST(self):
            if urlsplit(self.path).path != '/study/start':
                self.respond(404, 'Not found')
                return
            if self.headers.get('Origin') != config.origin:
                self.respond(403, 'Please open the study start link again.')
                return
            token = self.token()
            if not token:
                self.respond(409, 'Please allow cookies for this site, then open the study start link again.')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 64 or self.headers.get('Transfer-Encoding'):
                    raise ValueError()
                if self.headers.get('Content-Type', '').split(';', 1)[0] != 'application/x-www-form-urlencoded':
                    raise ValueError()
                if self.rfile.read(length) != b'start=1':
                    raise ValueError()
            except ValueError:
                self.respond(400, 'Invalid request. Please open the study start link again.')
                return
            try:
                self.redirect(allocator.assign(token))
            except sqlite3.Error:
                self.respond(503, 'Please try again shortly.')

    return http.server.ThreadingHTTPServer(address, Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18889)
    args = parser.parse_args()
    config = Config(**json.loads(args.config.read_text(encoding='utf-8')))
    # Protect both the SQLite database and its transaction journal.
    os.umask(0o077)
    server = make_server(('127.0.0.1', args.port), config, Allocator(args.database))
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
