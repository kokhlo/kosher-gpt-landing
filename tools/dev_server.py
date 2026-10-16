#!/usr/bin/env python3
"""Local preview of kosherno.app with a working form.

Serves the pages built by `python3 tools/build.py --dev` from .preview/ and
the shared files (assets/) from the repo root. Forms post to the local
kosher-forms Worker: run `npm run dev` in ../kosher-forms-worker, which prints
each mail instead of sending it.

    python3 tools/dev_server.py [port]      # default 8787
"""

import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / ".preview"
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("application/manifest+json", ".webmanifest")


def resolve(url_path):
    rel = unquote(urlparse(url_path).path).lstrip("/")
    for base in (PREVIEW, ROOT):
        candidate = (base / rel).resolve()
        if base.resolve() not in candidate.parents and candidate != base.resolve():
            continue
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if candidate.is_file():
            return candidate
    return None


class Handler(BaseHTTPRequestHandler):
    def send_file(self, path, status=200):
        body = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = resolve(self.path)
        if path:
            self.send_file(path)
        else:
            self.send_file(PREVIEW / "404.html", 404)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    if not (PREVIEW / "index.html").exists():
        sys.exit("No preview yet: run python3 tools/build.py --dev first.")
    print(f"KosherGPT preview on http://127.0.0.1:{port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
