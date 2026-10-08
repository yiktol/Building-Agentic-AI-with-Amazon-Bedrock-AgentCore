#!/usr/bin/env python3
"""Local dev server for the slides app WITH a working AI judge.

Plain `python3 -m http.server` (or serve.sh) serves the static files, but the
knowledge-check quiz's judge calls POST /judge — which only exists behind the
deployed CloudFront distribution. This server serves slides/ AND proxies /judge
to the deployed endpoint, adding the x-amz-content-sha256 body hash CloudFront's
OAC requires, so the AI judge works end-to-end on localhost exactly like
production.

The same proxy also forwards POST /assistant to the deployed course assistant
(the KB-grounded chatbot on the slides landing page), adding the same
x-amz-content-sha256 body hash, so the assistant works end-to-end on localhost
exactly like production.

Usage:
    python3 slides/serve_with_judge.py [PORT]        # default 8010
    JUDGE_UPSTREAM=https://agc.aws.yikyakyuk.com/judge python3 slides/serve_with_judge.py
    ASSISTANT_UPSTREAM=https://agc.aws.yikyakyuk.com/assistant python3 slides/serve_with_judge.py

Then open:  http://localhost:8010/quiz.html?m=1   (quiz judge)
            http://localhost:8010/index.html       (course assistant widget)
"""
import hashlib
import http.server
import os
import socketserver
import sys
import urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8010
DIR = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = os.environ.get("JUDGE_UPSTREAM", "https://agc.aws.yikyakyuk.com/judge")
ASSISTANT_UPSTREAM = os.environ.get(
    "ASSISTANT_UPSTREAM", "https://agc.aws.yikyakyuk.com/assistant"
)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def do_POST(self):
        # Route on the request path: /judge -> judge upstream, /assistant ->
        # assistant upstream. Both add the x-amz-content-sha256 body hash the
        # CloudFront OAC -> IAM Function URL requires.
        route = self.path.rstrip("/")
        if route == "/judge":
            upstream = UPSTREAM
        elif route == "/assistant":
            upstream = ASSISTANT_UPSTREAM
        else:
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        # CloudFront OAC -> IAM Function URL requires the SHA256 payload hash.
        body_hash = hashlib.sha256(body).hexdigest()
        req = urllib.request.Request(
            upstream, data=body, method="POST",
            headers={"content-type": "application/json",
                     "x-amz-content-sha256": body_hash},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = r.read()
                code = r.status
        except urllib.error.HTTPError as e:
            payload = e.read()
            code = e.code
        except Exception as e:
            payload = f'{{"error":"proxy failed: {e}"}}'.encode()
            code = 502
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def end_headers(self):
        # Avoid stale caching while developing.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class TCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    print(f"Serving {DIR} at http://localhost:{PORT}/")
    print(f"  /judge      ->  {UPSTREAM}  (proxied, body-hash added)")
    print(f"  /assistant  ->  {ASSISTANT_UPSTREAM}  (proxied, body-hash added)")
    print(f"Open: http://localhost:{PORT}/quiz.html?m=1  (quiz judge)")
    print(f"      http://localhost:{PORT}/index.html      (course assistant)")
    print("Ctrl-C to stop.")
    with TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
