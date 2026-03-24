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
import os
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

PORT = 8080
LIVE_MODE = False
DIR = Path(__file__).parent.resolve()
GEO_ANALYZER = Path.home() / "AIwork" / "projects" / "geo-analyzer"


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
        else:
            super().do_GET()

    def handle_analyze(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        brand = params.get("brand", [""])[0]
        queries = params.get("queries", [""])[0]
        competitors = params.get("competitors", [""])[0]

        if not brand:
            self.json_response({"error": "Missing brand"}, 400)
            return

        if LIVE_MODE:
            self.run_live_analysis(brand, queries, competitors)
        else:
            self.return_demo_data(brand, queries, competitors)

    def return_demo_data(self, brand, queries, competitors):
        """Return mock data with brand/queries substituted."""
        mock_path = DIR / "data" / "mock_data.json"
        with open(mock_path, encoding="utf-8") as f:
            data = json.load(f)

        # Substitute brand name throughout
        original_brand = data["brand"]
        data["brand"] = brand
        if "summary" in data and "headline" in data["summary"]:
            data["summary"]["headline"] = data["summary"]["headline"].replace(original_brand, brand)

        # Substitute in competitive table "you" row
        for row in data.get("competitive", {}).get("competitors_table", []):
            if row.get("is_you"):
                row["brand"] = f"{brand} (你)"

        # Substitute query list if user provided custom ones
        query_list = [q.strip() for q in queries.split(",") if q.strip()]
        if query_list:
            data["dashboard"]["top_queries"] = data["dashboard"]["top_queries"][:len(query_list)]
            for i, q in enumerate(query_list):
                if i < len(data["dashboard"]["top_queries"]):
                    data["dashboard"]["top_queries"][i]["query"] = q

        # Substitute competitors
        if competitors:
            comp_list = [c.strip() for c in competitors.split(",") if c.strip()]
            if comp_list:
                data["competitors"] = comp_list
                for i, c in enumerate(comp_list):
                    if i < len(data["competitive"]["competitors_table"]):
                        row = data["competitive"]["competitors_table"][i]
                        if not row.get("is_you"):
                            row["brand"] = c

        self.json_response(data)

    def run_live_analysis(self, brand, queries, competitors):
        """Run Google AIO + Perplexity scrapers via geo-analyzer."""
        venv_python = GEO_ANALYZER / ".venv" / "bin" / "python"
        screenshots_dir = str(DIR / "screenshots")

        cmd = [
            str(venv_python), "-m", "geo.live_analyze",
            "--brand", brand,
            "--queries", queries if queries else brand,
            "--screenshots-dir", screenshots_dir,
            "--platforms", "google_aio,perplexity",
        ]
        if competitors:
            cmd.extend(["--competitors", competitors])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(GEO_ANALYZER),
            )

            if result.returncode != 0:
                self.return_demo_data(brand, queries, competitors)
                return

            live_data = json.loads(result.stdout)

            # Merge live results into mock data template for full UI
            mock_path = DIR / "data" / "mock_data.json"
            with open(mock_path, encoding="utf-8") as f:
                template = json.load(f)

            template["brand"] = brand
            template["live_mode"] = True

            # Build platform stats from live data
            pstats = live_data.get("platform_stats", {})
            platforms_ui = []
            highlights = []
            total_mentioned = 0
            total_queries = 0

            platform_icons = {"google_aio": "🔗", "perplexity": "🔍"}
            platform_names = {"google_aio": "Google AI Overview", "perplexity": "Perplexity"}

            for pname, stats in pstats.items():
                rate = stats.get("citation_rate", 0)
                platforms_ui.append({
                    "name": platform_names.get(pname, pname),
                    "icon": platform_icons.get(pname, "🤖"),
                    "coverage": rate,
                })
                total_mentioned += stats.get("mentioned_count", 0)
                total_queries += stats.get("queries_count", 0)

                if pname == "google_aio":
                    aio_count = stats.get("has_ai_overview_count", 0)
                    highlights.append({"icon": "🔗", "text": f"Google AI Overview：{aio_count}/{stats['queries_count']} 個查詢出現 AI 概覽，引用率 {rate}%"})
                elif pname == "perplexity":
                    highlights.append({"icon": "🔍", "text": f"Perplexity：引用率 {rate}%"})

            overall_rate = round(total_mentioned / total_queries * 100, 1) if total_queries > 0 else 0
            highlights.append({"icon": "🔗", "text": f"引用來源 {len(live_data.get('source_domains', {}))} 個不同網域"})

            template["summary"]["headline"] = f"{brand} 在 AI 搜尋的綜合引用率為 {overall_rate}%（{total_mentioned}/{total_queries} 個查詢被引用）"
            template["summary"]["verdict"] = "good" if overall_rate >= 40 else "warning" if overall_rate >= 20 else "bad"
            template["summary"]["highlights"] = highlights

            template["dashboard"]["citation_rate"] = overall_rate
            template["dashboard"]["platforms"] = platforms_ui

            # Inject source domains
            template["source_domains"] = live_data.get("source_domains", {})

            # Inject real query results
            template["live_results"] = live_data.get("results", [])

            # Competitive table — use brand name
            for row in template.get("competitive", {}).get("competitors_table", []):
                if row.get("is_you"):
                    row["brand"] = f"{brand} (你)"

            self.json_response(template)

        except subprocess.TimeoutExpired:
            self.json_response({"error": "Analysis timed out (180s). Try fewer queries."}, 504)
        except json.JSONDecodeError:
            self.return_demo_data(brand, queries, competitors)
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

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
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


def main():
    parse_args()
    server = http.server.HTTPServer(("0.0.0.0", PORT), GEOHandler)
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
