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
import urllib.parse
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

PORT = 8080
LIVE_MODE = False
DIR = Path(__file__).parent.resolve()
GEO_ANALYZER = Path.home() / "AIwork" / "projects" / "geo-analyzer"
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
        elif re.match(r"^/api/history/[a-f0-9]+$", parsed.path):
            record_id = parsed.path.split("/")[-1]
            self.handle_history_detail(record_id)
        else:
            super().do_GET()

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
        limit = int(params.get("limit", ["50"])[0])
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
    class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
    server = ThreadedServer(("0.0.0.0", PORT), GEOHandler)
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
