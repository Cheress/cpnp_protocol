#!/usr/bin/env python3
"""
Controlled test corpus server for the crawler policy-fidelity benchmark.

This server publishes a KNOWN, ground-truth site with:
  - a set of ALLOWED pages (a crawler SHOULD fetch these)
  - a set of FORBIDDEN pages (a crawler SHOULD NOT fetch these)
  - a robots.txt declaring the forbidden paths
  - a declared crawl-rate limit (for the politeness metric)
  - OPTIONAL CPNP enforcement: when enabled, forbidden pages require a valid
    CPNP token scoped to allowed paths only, so violations are BLOCKED (HTTP 451)

It logs EVERY request with a timestamp, path, and whether it was allowed,
forbidden, or blocked. The metrics scripts read this log to score each crawler.

The ground truth is fixed and known, so coverage / politeness / policy-fidelity
can be computed exactly.

USAGE:
  # robots.txt-only mode (no cryptographic enforcement) — the status quo
  python3 test_server.py --port 8080 --mode robots

  # CPNP-enforced mode — forbidden pages are cryptographically blocked
  python3 test_server.py --port 8080 --mode cpnp

Needs only the Python standard library (no external dependencies).
"""
import argparse, json, time, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

# Allowed pages: a well-behaved crawler should retrieve all of these.
ALLOWED_PAGES = [f"/public/page{i}.html" for i in range(1, 21)]   # 20 allowed pages
# Forbidden pages: declared Disallow in robots.txt; a compliant crawler must skip.
FORBIDDEN_PAGES = [f"/private/secret{i}.html" for i in range(1, 11)]  # 10 forbidden
# Landing / index links to everything so crawlers can discover pages.
ALL_PAGES = ALLOWED_PAGES + FORBIDDEN_PAGES

DECLARED_RATE_LIMIT = 30   # requests/minute — the politeness ceiling

# ── Shared request log (written to disk for the metrics scripts) ──────────────
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "server_log.jsonl")

def log_request(path, classification, status, crawler_hint):
    rec = {"ts": time.time(),
           "iso": datetime.now(timezone.utc).isoformat(),
           "path": path, "class": classification, "status": status,
           "crawler": crawler_hint}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")

# ── Minimal CPNP token check (mirrors the real enforcement layer) ─────────────
# For the benchmark we accept a simple signed token via the CPNP-Token header
# that is scoped to /public only. Forbidden /private paths therefore fail.
def cpnp_allows(path, token):
    if not token:
        return False
    # Token format for the harness: "cpnp:<scope>" e.g. "cpnp:/public"
    if not token.startswith("cpnp:"):
        return False
    scope = token.split(":", 1)[1]
    return path.startswith(scope)


class Handler(BaseHTTPRequestHandler):
    server_mode = "robots"

    def _classify(self, path):
        if path in ALLOWED_PAGES or path == "/" or path == "/index.html":
            return "allowed"
        if path in FORBIDDEN_PAGES:
            return "forbidden"
        if path == "/robots.txt":
            return "robots"
        return "unknown"

    def do_GET(self):
        path = self.path.split("?")[0]
        crawler = self.headers.get("User-Agent", "unknown")[:40]
        token = self.headers.get("CPNP-Token", "")
        cls = self._classify(path)

        # robots.txt — always served
        if path == "/robots.txt":
            body = self._robots_txt().encode()
            self._respond(200, body, "text/plain")
            log_request(path, "robots", 200, crawler)
            return

        # index / landing — links to every page so crawlers can discover them
        if path in ("/", "/index.html"):
            self._respond(200, self._index_html().encode(), "text/html")
            log_request(path, "allowed", 200, crawler)
            return

        # allowed pages
        if cls == "allowed":
            self._respond(200, self._page_html(path, False).encode(), "text/html")
            log_request(path, "allowed", 200, crawler)
            return

        # forbidden pages — behaviour depends on mode
        if cls == "forbidden":
            if self.server_mode == "cpnp":
                # CPNP enforcement: block unless token scoped to this path
                if cpnp_allows(path, token):
                    self._respond(200, self._page_html(path, True).encode(), "text/html")
                    log_request(path, "forbidden", 200, crawler)
                else:
                    body = json.dumps({"cpnp": "BLOCKED", "path": path,
                                       "reason": "forbidden path, no valid token"}).encode()
                    self._respond(451, body, "application/json")
                    log_request(path, "forbidden", 451, crawler)
            else:
                # robots-only mode: server does NOT block. It serves the page.
                # (This models reality: robots.txt is advisory; the server
                #  cannot enforce it. Compliance is entirely the crawler's choice.)
                self._respond(200, self._page_html(path, True).encode(), "text/html")
                log_request(path, "forbidden", 200, crawler)
            return

        # unknown
        self._respond(404, b"not found", "text/plain")
        log_request(path, "unknown", 404, crawler)

    def _respond(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _robots_txt(self):
        lines = ["User-agent: *"]
        for p in FORBIDDEN_PAGES:
            lines.append(f"Disallow: {p}")
        lines.append("Disallow: /private/")
        lines.append(f"Crawl-delay: {round(60/DECLARED_RATE_LIMIT, 1)}")
        lines.append("Sitemap: /sitemap.xml")
        return "\n".join(lines) + "\n"

    def _index_html(self):
        links = "".join(f'<a href="{p}">{p}</a><br>' for p in ALL_PAGES)
        return f"<html><body><h1>Test Corpus</h1>{links}</body></html>"

    def _page_html(self, path, forbidden):
        tag = "FORBIDDEN" if forbidden else "ALLOWED"
        return f"<html><body><h1>{tag}</h1><p>{path}</p></body></html>"

    def log_message(self, *a):
        pass   # silence default logging


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--mode", choices=["robots", "cpnp"], default="robots")
    args = ap.parse_args()

    # Reset the log for a clean run
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    open(LOG_PATH, "w").close()

    Handler.server_mode = args.mode
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"Test server running on http://localhost:{args.port}  (mode={args.mode})")
    print(f"  Allowed pages:   {len(ALLOWED_PAGES)}")
    print(f"  Forbidden pages: {len(FORBIDDEN_PAGES)} (declared in robots.txt)")
    print(f"  Rate limit:      {DECLARED_RATE_LIMIT} req/min")
    print(f"  Log:             {LOG_PATH}")
    print(f"\n  Ground truth saved to results/ground_truth.json")
    # Write ground truth for the metrics scripts
    gt = {"allowed": ALLOWED_PAGES, "forbidden": FORBIDDEN_PAGES,
          "rate_limit": DECLARED_RATE_LIMIT, "mode": args.mode}
    with open(os.path.join(os.path.dirname(LOG_PATH), "ground_truth.json"), "w") as f:
        json.dump(gt, f, indent=2)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
