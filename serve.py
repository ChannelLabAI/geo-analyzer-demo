#!/usr/bin/env python3
"""GEO Analyzer Demo — HTTP Server with API.

Modes:
    Demo mode (default): Returns mock data from data/mock_data.json
    Live mode: Runs geo-analyzer CLI and returns real results

Usage:
    python3 serve.py [--live] [--port 8080]
"""

import http.server
import json
import re
import socketserver
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

GEO_ANALYZER_VENV_PYTHON = Path.home() / "projects" / "geo-analyzer" / ".venv" / "bin" / "python3"

_SITE_AUDIT_SCRIPT = """
import asyncio, sys, json
sys.path.insert(0, sys.argv[1])
from geo.site_audit import audit_site
result = asyncio.run(audit_site(sys.argv[2]))
print(json.dumps(result.to_dict(), ensure_ascii=False))
"""

_BRAND_SCORE_SCRIPT = """
import asyncio, sys, json
sys.path.insert(0, sys.argv[1])
from geo.scoring import compute_brand_geo_score
result = asyncio.run(compute_brand_geo_score(sys.argv[2], sys.argv[3]))
print(json.dumps(result.to_dict(), ensure_ascii=False))
"""

# ---------------------------------------------------------------------------
# Brand GEO Score job store (in-memory, thread-safe, 30-min TTL)
# ---------------------------------------------------------------------------

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_JOB_TTL = 1800  # 30 minutes


def _create_brand_score_job(url: str, brand: str) -> str:
    """Create a job entry and spawn the background computation thread."""
    job_id = str(uuid.uuid4()).replace("-", "")[:16]
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": time.time(),
            "estimated_total": 45.0,
        }
    t = threading.Thread(target=_run_brand_score_job, args=(job_id, url, brand), daemon=True)
    t.start()
    return job_id


def _run_brand_score_job(job_id: str, url: str, brand: str) -> None:
    """Background thread: run compute_brand_geo_score via subprocess and store result."""
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id]["status"] = "running"
            _JOBS[job_id]["progress"] = 5

    try:
        result = subprocess.run(
            [
                str(GEO_ANALYZER_VENV_PYTHON), "-c", _BRAND_SCORE_SCRIPT,
                str(GEO_ANALYZER), url, brand,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        with _JOBS_LOCK:
            if job_id not in _JOBS:
                return
            if result.returncode != 0:
                err = result.stderr.strip()[:400] or "brand-score subprocess failed"
                _JOBS[job_id]["status"] = "error"
                _JOBS[job_id]["error"] = err
                _JOBS[job_id]["progress"] = 0
            else:
                data = json.loads(result.stdout)
                _JOBS[job_id]["status"] = "done"
                _JOBS[job_id]["result"] = data
                _JOBS[job_id]["progress"] = 100
    except subprocess.TimeoutExpired:
        with _JOBS_LOCK:
            if job_id in _JOBS:
                _JOBS[job_id]["status"] = "error"
                _JOBS[job_id]["error"] = "Analysis timed out (180s)"
    except json.JSONDecodeError as e:
        with _JOBS_LOCK:
            if job_id in _JOBS:
                _JOBS[job_id]["status"] = "error"
                _JOBS[job_id]["error"] = f"Invalid JSON from analyzer: {e}"
    except Exception as e:
        with _JOBS_LOCK:
            if job_id in _JOBS:
                _JOBS[job_id]["status"] = "error"
                _JOBS[job_id]["error"] = str(e)


def _cleanup_expired_jobs() -> None:
    """Background thread: sweep _JOBS every 5 minutes, drop entries older than TTL."""
    while True:
        time.sleep(300)
        cutoff = time.time() - _JOB_TTL
        with _JOBS_LOCK:
            expired = [jid for jid, j in _JOBS.items() if j["created_at"] < cutoff]
            for jid in expired:
                del _JOBS[jid]


from website_diagnostics import run_all_diagnostics, generate_llmstxt, validate_url

PORT = 8080
LIVE_MODE = False
DIR = Path(__file__).parent.resolve()
GEO_ANALYZER = Path.home() / "projects" / "geo-analyzer"
DB_PATH = DIR / "data" / "history.db"


def init_db():
    """Initialize SQLite database for analysis history."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            brand TEXT NOT NULL,
            queries TEXT,
            competitors TEXT,
            platforms TEXT,
            overall_rate REAL,
            verdict TEXT,
            live_mode INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at DESC)")
    conn.commit()
    conn.close()


def save_history(brand, queries, competitors, platforms, data):
    """Save analysis result to history. Returns the record ID."""
    record_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    summary = data.get("summary", {})
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO history (id, brand, queries, competitors, platforms, overall_rate, verdict, live_mode, created_at, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            record_id,
            brand,
            queries,
            competitors,
            platforms,
            summary.get("overall_rate"),
            summary.get("verdict"),
            1 if data.get("live_mode") else 0,
            now,
            json.dumps(data, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()
    return record_id


def get_history_list(limit=50):
    """Get recent analysis history (metadata only)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, brand, queries, competitors, platforms, overall_rate, verdict, live_mode, created_at FROM history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_history_detail(record_id):
    """Get full analysis result by ID."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM history WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["data"] = json.loads(result["data"])
    return result


def delete_history(record_id):
    """Delete a history record. Returns True if deleted."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_brand_trend(brand):
    """Get chronological trend data for a brand."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, overall_rate, verdict, live_mode, created_at, data FROM history WHERE brand = ? ORDER BY created_at ASC",
        (brand,),
    ).fetchall()
    conn.close()

    points = []
    for r in rows:
        data = json.loads(r["data"])
        platform_rates = {}
        for p in data.get("platforms", []):
            platform_rates[p["id"]] = p.get("citation_rate", 0)
        points.append({
            "id": r["id"],
            "date": r["created_at"],
            "overall_rate": r["overall_rate"],
            "live_mode": bool(r["live_mode"]),
            "platform_rates": platform_rates,
        })
    return points


def parse_args():
    global PORT, LIVE_MODE
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--live":
            LIVE_MODE = True
        elif args[i] == "--port" and i + 1 < len(args):
            PORT = int(args[i + 1])
            i += 1
        elif args[i].isdigit():
            PORT = int(args[i])
        i += 1


class GEOHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/analyze":
            self.handle_analyze(parsed)
        elif parsed.path == "/api/status":
            self.json_response({"mode": "live" if LIVE_MODE else "demo", "geo_analyzer": str(GEO_ANALYZER)})
        elif parsed.path == "/api/history":
            self.handle_history_list(parsed)
        elif parsed.path == "/api/history/trend":
            self.handle_trend(parsed)
        elif parsed.path == "/api/site-audit":
            self.handle_site_audit(parsed)
        elif parsed.path == "/api/website-diagnostics":
            self.handle_diagnostics(parsed)
        elif parsed.path == "/api/llmstxt-download":
            self.handle_llmstxt_download(parsed)
        elif re.match(r"^/api/history/[a-f0-9]+$", parsed.path):
            record_id = parsed.path.split("/")[-1]
            self.handle_history_detail(record_id)
        elif re.match(r"^/api/brand-score/[a-f0-9]{16}$", parsed.path):
            job_id = parsed.path.split("/")[-1]
            self.handle_brand_score_get(job_id)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/brand-score":
            self.handle_brand_score_post(parsed)
        else:
            self.json_response({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        """Handle CORS preflight for Next.js dev proxy."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def handle_brand_score_post(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        url = params.get("url", [""])[0]
        brand = params.get("brand", [""])[0].strip()

        if not url or not url.startswith(("http://", "https://")):
            self.json_response({"error": "Missing or invalid URL (must start with http:// or https://)"}, 400)
            return
        if not brand:
            self.json_response({"error": "Missing brand name"}, 400)
            return
        ssrf_err = validate_url(url)
        if ssrf_err:
            self.json_response({"error": ssrf_err}, 400)
            return

        job_id = _create_brand_score_job(url, brand)
        self.json_response({"job_id": job_id, "estimated_total": 45.0}, 201)

    def handle_brand_score_get(self, job_id: str):
        with _JOBS_LOCK:
            job = _JOBS.get(job_id)
        if job is None:
            self.json_response({"error": "Job not found or expired"}, 404)
            return
        self.json_response({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "result": job["result"],
            "error": job["error"],
            "estimated_total": job["estimated_total"],
        })

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if re.match(r"^/api/history/[a-f0-9]+$", parsed.path):
            record_id = parsed.path.split("/")[-1]
            if delete_history(record_id):
                self.json_response({"ok": True})
            else:
                self.json_response({"error": "Not found"}, 404)
        else:
            self.json_response({"error": "Not found"}, 404)

    def handle_history_list(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        limit = min(int(params.get("limit", ["50"])[0]), 200)
        records = get_history_list(limit)
        self.json_response(records)

    def handle_history_detail(self, record_id):
        record = get_history_detail(record_id)
        if record:
            self.json_response(record)
        else:
            self.json_response({"error": "Not found"}, 404)

    def handle_trend(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        brand = params.get("brand", [""])[0]
        if not brand:
            self.json_response({"error": "Missing brand"}, 400)
            return
        points = get_brand_trend(brand)
        self.json_response({"brand": brand, "points": points})

    def handle_site_audit(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        url = params.get("url", [""])[0]
        if not url or not url.startswith(("http://", "https://")):
            self.json_response({"error": "Missing or invalid URL"}, 400)
            return
        from website_diagnostics import validate_url
        ssrf_err = validate_url(url)
        if ssrf_err:
            self.json_response({"error": ssrf_err}, 400)
            return
        try:
            result = subprocess.run(
                [str(GEO_ANALYZER_VENV_PYTHON), "-c", _SITE_AUDIT_SCRIPT, str(GEO_ANALYZER), url],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                self.json_response({"error": result.stderr[:300] or "site_audit failed"}, 500)
                return
            self.json_response(json.loads(result.stdout))
        except subprocess.TimeoutExpired:
            self.json_response({"error": "Site audit timed out"}, 504)
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_diagnostics(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        url = params.get("url", [""])[0]
        if not url or not url.startswith(("http://", "https://")):
            self.json_response({"error": "Missing or invalid URL (must start with http:// or https://)"}, 400)
            return
        ssrf_err = validate_url(url)
        if ssrf_err:
            self.json_response({"error": ssrf_err}, 400)
            return
        if LIVE_MODE:
            try:
                data = run_all_diagnostics(url)
                self.json_response(data)
            except Exception as e:
                self.json_response({"error": str(e)}, 500)
        else:
            # Demo mode: return mock diagnostics
            mock_path = DIR / "data" / "mock_diagnostics.json"
            if mock_path.exists():
                with open(mock_path, encoding="utf-8") as f:
                    self.json_response(json.load(f))
            else:
                self.json_response({"error": "Mock diagnostics not available"}, 404)

    def handle_llmstxt_download(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        url = params.get("url", [""])[0]
        file_type = params.get("type", ["llmstxt"])[0]
        if not url or not url.startswith(("http://", "https://")):
            self.json_response({"error": "Missing or invalid URL"}, 400)
            return
        ssrf_err = validate_url(url)
        if ssrf_err:
            self.json_response({"error": ssrf_err}, 400)
            return
        if not LIVE_MODE:
            # Demo mode: serve mock llms.txt from mock_diagnostics.json
            mock_path = DIR / "data" / "mock_diagnostics.json"
            content = "# Demo llms.txt\n> Switch to live mode for real generation.\n"
            if mock_path.exists():
                with open(mock_path, encoding="utf-8") as f:
                    mock = json.load(f)
                key = "generated_llmstxt_full" if file_type == "full" else "generated_llmstxt"
                content = mock.get("llmstxt", {}).get(key, content)
            filename = "llms-full.txt" if file_type == "full" else "llms.txt"
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        try:
            data = generate_llmstxt(url)
            content = data.get("generated_llmstxt_full" if file_type == "full" else "generated_llmstxt", "")
            filename = "llms-full.txt" if file_type == "full" else "llms.txt"
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def handle_analyze(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        brand = params.get("brand", [""])[0]
        queries = params.get("queries", [""])[0]
        competitors = params.get("competitors", [""])[0]
        platforms = params.get("platforms", ["google_aio,perplexity,gemini"])[0]

        if not brand:
            self.json_response({"error": "Missing brand"}, 400)
            return

        if LIVE_MODE:
            self.run_live_analysis(brand, queries, competitors, platforms)
        else:
            self.return_demo_data(brand, queries, competitors, platforms)

    def return_demo_data(self, brand, queries, competitors, platforms="gemini"):
        """Return raw mock data — all substitution happens client-side."""
        mock_path = DIR / "data" / "mock_data.json"
        with open(mock_path, encoding="utf-8") as f:
            data = json.load(f)

        record_id = save_history(brand, queries, competitors, platforms, data)
        data["history_id"] = record_id
        self.json_response(data)

    def run_live_analysis(self, brand, queries, competitors, platforms="google_aio,perplexity,gemini"):
        """Run geo-analyzer for main brand + competitors sequentially."""
        try:
            # 1. Analyze main brand
            main_result = self._run_single_brand(brand, queries, platforms)
            if main_result is None:
                return  # error already sent

            output = main_result

            # 2. Analyze competitors sequentially (respect rate limits)
            comp_list = [c.strip() for c in competitors.split(",") if c.strip()] if competitors else []
            comp_list = comp_list[:3]  # max 3 competitors

            if comp_list:
                comp_results = []
                for comp_brand in comp_list:
                    comp_data = self._run_single_brand(comp_brand, queries, platforms, timeout=120)
                    if comp_data:
                        comp_results.append({
                            "brand": comp_data["brand"],
                            "overall_rate": comp_data["summary"]["overall_rate"],
                            "total_mentioned": comp_data["summary"]["total_mentioned"],
                            "total_queries": comp_data["summary"]["total_queries"],
                            "platforms": [
                                {"id": p["id"], "name": p["name"], "icon": p["icon"],
                                 "citation_rate": p["citation_rate"],
                                 "mentioned_count": p["mentioned_count"],
                                 "queries_count": p["queries_count"]}
                                for p in comp_data["platforms"]
                            ],
                        })
                    else:
                        comp_results.append({
                            "brand": comp_brand,
                            "overall_rate": None,
                            "total_mentioned": 0,
                            "total_queries": 0,
                            "platforms": [],
                            "error": "Analysis failed",
                        })

                output["competitors"] = comp_results

            record_id = save_history(brand, queries, competitors, platforms, output)
            output["history_id"] = record_id
            self.json_response(output)

        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def _run_single_brand(self, brand, queries, platforms, timeout=300):
        """Run geo-analyzer for a single brand. Returns parsed output dict or None on error."""
        venv_python = GEO_ANALYZER / ".venv" / "bin" / "python"
        screenshots_dir = str(DIR / "screenshots")

        cmd = [
            str(venv_python), "-m", "geo.live_analyze",
            "--brand", brand,
            "--queries", queries if queries else brand,
            "--screenshots-dir", screenshots_dir,
            "--platforms", platforms,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, cwd=str(GEO_ANALYZER),
            )

            if result.returncode != 0:
                stderr = result.stderr[:500] if result.stderr else "Unknown error"
                self.json_response({"error": f"Analysis failed for {brand}: {stderr}"}, 500)
                return None

            live_data = json.loads(result.stdout)

            pstats = live_data.get("platform_stats", {})
            platform_icons = {"google_aio": "🔗", "perplexity": "🔍", "gemini": "✨"}
            platform_labels = {"google_aio": "Google AI Overview", "perplexity": "Perplexity", "gemini": "Gemini"}

            total_mentioned = 0
            total_queries = 0
            platform_cards = []

            for pname, stats in pstats.items():
                rate = stats.get("citation_rate", 0)
                mentioned = stats.get("mentioned_count", 0)
                count = stats.get("queries_count", 0)
                total_mentioned += mentioned
                total_queries += count
                platform_cards.append({
                    "id": pname,
                    "name": platform_labels.get(pname, pname),
                    "icon": platform_icons.get(pname, "🤖"),
                    "citation_rate": rate,
                    "mentioned_count": mentioned,
                    "queries_count": count,
                    "position_counts": stats.get("position_counts", {}),
                })

            overall_rate = round(total_mentioned / total_queries * 100, 1) if total_queries > 0 else 0
            verdict = "good" if overall_rate >= 40 else "warning" if overall_rate >= 20 else "bad"

            return {
                "brand": brand,
                "live_mode": True,
                "generated_at": live_data.get("generated_at", ""),
                "summary": {
                    "overall_rate": overall_rate,
                    "total_mentioned": total_mentioned,
                    "total_queries": total_queries,
                    "verdict": verdict,
                },
                "platforms": platform_cards,
                "source_domains": live_data.get("source_domains", {}),
                "results": live_data.get("results", []),
            }

        except subprocess.TimeoutExpired:
            self.json_response({"error": f"Analysis timed out for {brand}"}, 504)
            return None
        except json.JSONDecodeError as e:
            self.json_response({"error": f"Invalid JSON from analyzer for {brand}: {e}"}, 500)
            return None

    def json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress static file logs, show API calls
        if args and "/api/" in str(args[0]):
            super().log_message(format, *args)


def main():
    parse_args()
    init_db()
    # Start background job cleanup thread
    cleanup_thread = threading.Thread(target=_cleanup_expired_jobs, daemon=True)
    cleanup_thread.start()
    class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
    server = ThreadedServer(("127.0.0.1", PORT), GEOHandler)
    mode = "LIVE" if LIVE_MODE else "DEMO"
    url = f"http://localhost:{PORT}/"

    print(f"\n  GEO Analyzer Demo Server")
    print(f"  ───────────────────────")
    print(f"  URL:   {url}")
    print(f"  Mode:  {mode}")
    print(f"  Dir:   {DIR}")
    if LIVE_MODE:
        print(f"  Geo:   {GEO_ANALYZER}")
    print(f"\n  Press Ctrl+C to stop\n")

    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
