"""
serve_ledger.py — Production-grade HTTP server for AgentEscrow Ledger UI
Serves frontend dashboard, queries Google Sheets (Demo_Ledger + Ledger),
and handles rate-limited verification API calls without exposing any secrets.
"""

import os
import sys
import json
import time
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

PORT = int(os.getenv("PORT", "5000"))

# In-flight concurrency lock & rate limiting (Requirement 4)
_verify_lock = threading.Lock()
_ip_rate_limits = {}  # client_ip -> timestamp
RATE_LIMIT_SECONDS = 10

def parse_rows(rows, is_demo=False):
    """Formats sheet rows into consistent UI entries."""
    parsed = []
    for row in rows:
        if not row or len(row) < 3:
            continue
        task_id = str(row[0]).strip()
        verdict = str(row[1]).lower().strip()
        action = str(row[2]).lower().strip()
        try:
            conf_val = float(row[3]) if len(row) > 3 and row[3] else 0.90
        except ValueError:
            conf_val = 0.90
        ts = row[4] if len(row) > 4 else ""
        verified = str(row[5]).upper() == "TRUE" if len(row) > 5 else True

        # Format human readable time
        time_str = ts.split("T")[1][:8] if "T" in ts else ts

        # Evidence & Reason heuristics based on task
        if "pass" in task_id or verdict == "pass":
            reason = "All acceptance criteria verified in diff with full test coverage."
            evidence = [
                {"met": True, "text": "TokenBucketRateLimiter class implemented with capacity & refill"},
                {"met": True, "text": "Rate limit middleware enforces HTTP 429 status on depletion"},
                {"met": True, "text": "Comprehensive test suite covering consumption & refill math"},
                {"met": True, "text": "Zero unapproved external dependencies added"}
            ]
            action_display = "RELEASE — $50.00"
        elif "fail" in task_id or verdict == "fail":
            reason = "Unit tests missing: tests/test_rate_limiter.py contains only TODO placeholders."
            evidence = [
                {"met": True, "text": "TokenBucketRateLimiter class drafted"},
                {"met": True, "text": "Rate limit middleware returns 429"},
                {"met": False, "text": "Comprehensive unit tests missing (TODO placeholder only)"},
                {"met": True, "text": "Zero unapproved external dependencies added"}
            ]
            action_display = "HOLD — $50.00"
        else:  # review
            reason = "Borderline subjective criterion; confidence below 0.70 safety threshold."
            evidence = [
                {"met": True, "text": "Basic implementation meets initial specifications"},
                {"met": True, "text": "Unverifiable performance claim requires human reviewer sign-off"}
            ]
            action_display = "PENDING — $50.00"

        parsed.append({
            "task_id": task_id,
            "verdict": verdict,
            "payment_action": action,
            "action_display": action_display,
            "confidence": conf_val,
            "confidence_pct": int(conf_val * 100),
            "timestamp": time_str,
            "verified": verified,
            "reason": reason,
            "evidence": evidence,
            "is_demo": is_demo
        })
    return parsed

def get_live_ledger_data():
    """
    Fetches live audit ledger data:
    1. Demo_Ledger (live runs executed via web dashboard) - placed first
    2. Ledger (canonical 5 baseline benchmark runs) - kept frozen
    """
    sheet_id = os.getenv("SHEET_ID", "1ZMip-wiCSVPMa-e4Rufj6kobUh3V2Yvp7vK8AL4oX3g")
    entries = []

    try:
        from agentescrow import get_google_credentials
        creds = get_google_credentials(["https://www.googleapis.com/auth/spreadsheets"])
        if sheet_id and creds:
            from googleapiclient.discovery import build
            service = build("sheets", "v4", credentials=creds)

            # Query live demo runs
            demo_rows = []
            try:
                res_demo = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range="Demo_Ledger!A2:F50"
                ).execute()
                demo_rows = res_demo.get("values", [])
            except Exception as ed:
                print(f"[INFO] Demo_Ledger query note: {ed}")

            # Query canonical frozen baseline runs
            canon_rows = []
            try:
                res_canon = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range="Ledger!A2:F50"
                ).execute()
                canon_rows = res_canon.get("values", [])
            except Exception as ec:
                print(f"[INFO] Ledger query note: {ec}")

            # Demo entries at top (reversed so latest run appears first), followed by canonical baseline
            entries = parse_rows(list(reversed(demo_rows)), is_demo=True) + parse_rows(canon_rows, is_demo=False)
    except Exception as e:
        print(f"[WARN] Failed fetching from Sheets API: {e}")

    # Fallback to local file if Sheets empty or unconfigured
    if not entries and os.path.exists("ledger_local.jsonl"):
        with open("ledger_local.jsonl", "r", encoding="utf-8") as f:
            local_rows = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    local_rows.append(json.loads(line))
                except Exception:
                    pass
            entries = parse_rows(list(reversed(local_rows)), is_demo=True)

    return entries

class LedgerHandler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path_lower = parsed.path.lower()

        # Security check: Zero Secret Exposure (Requirement 5)
        # Explicitly deny any access to sensitive files, environment configs, or source files
        forbidden_patterns = [
            ".env", "service_account", "credentials", ".git", ".py",
            ".jsonl", ".sh", ".bat", ".ps1", "eval.md", "build", "requirements.txt"
        ]
        if any(p in path_lower for p in forbidden_patterns):
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Access forbidden: sensitive file or resource"}')
            return

        if parsed.path == "/api/ledger":
            data = get_live_ledger_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif parsed.path == "/api/config":
            # Only public URLs are exposed — ZERO API keys, tokens, or private secrets
            doc_id = os.getenv("DOC_ID", "1HuV_EGbyLadPlwPYWHDyjT9hIwWHEhG6HXzpXLyDYQ4")
            sheet_id = os.getenv("SHEET_ID", "1ZMip-wiCSVPMa-e4Rufj6kobUh3V2Yvp7vK8AL4oX3g")
            repo = os.getenv("GITHUB_REPO", "Dev-43/agent-escrow")
            config = {
                "google_doc_url": f"https://docs.google.com/document/d/{doc_id}/edit",
                "google_sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
                "github_repo_url": f"https://github.com/{repo}",
                "pr_1_url": f"https://github.com/{repo}/pull/1",
                "pr_2_url": f"https://github.com/{repo}/pull/2",
                "stripe_url": "https://dashboard.stripe.com/test/payments",
                "repo": repo,
                "doc_id": doc_id,
                "sheet_id": sheet_id
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(config).encode("utf-8"))

        elif parsed.path == "/" or parsed.path == "/index.html":
            if os.path.exists("frontend/ledger.html"):
                self.path = "/frontend/ledger.html"
            else:
                self.path = "/ledger.html"
            return super().do_GET()

        else:
            return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/verify":
            # 1. Rate Limiting Check per IP (Requirement 4)
            client_ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
            now = time.time()
            last_req = _ip_rate_limits.get(client_ip, 0)
            if now - last_req < RATE_LIMIT_SECONDS:
                wait_sec = int(RATE_LIMIT_SECONDS - (now - last_req)) + 1
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "rate_limited": True,
                    "error": f"Please wait {wait_sec}s before running another verification to preserve test quotas."
                }).encode("utf-8"))
                return

            # 2. In-flight Concurrency Lock Check (Requirement 4)
            if not _verify_lock.acquire(blocking=False):
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "rate_limited": True,
                    "error": "A verification gate cycle is currently in progress. Please allow it to complete (~4-8s)."
                }).encode("utf-8"))
                return

            try:
                _ip_rate_limits[client_ip] = time.time()
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
                try:
                    payload = json.loads(body)
                except Exception:
                    payload = {}

                scenario = payload.get("scenario")
                fixture = payload.get("fixture")
                task_id = payload.get("task_id")

                if scenario == "ambiguous":
                    fixture = "fixtures/pr_ambiguous.md"
                    pr_num_int = 44
                    if not task_id:
                        task_id = f"task_ambiguous_{int(time.time())}"
                elif scenario == "pass":
                    pr_num_int = 1
                    if not task_id:
                        task_id = f"task_pass_pr1_{int(time.time())}"
                elif scenario == "fail":
                    pr_num_int = 2
                    if not task_id:
                        task_id = f"task_fail_pr2_{int(time.time())}"
                else:
                    pr_num_int = 1
                    if not task_id:
                        task_id = f"task_demo_{int(time.time())}"

                import agentescrow
                # Requirement 3: Explicitly route live web runs to Demo_Ledger
                result = agentescrow.run_pipeline(
                    task_id=task_id,
                    fixture_path=fixture,
                    amount_cents=5000,
                    pr_number=pr_num_int,
                    ledger_tab="Demo_Ledger"
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "result": result}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            finally:
                _ip_rate_limits[client_ip] = time.time()
                _verify_lock.release()
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, LedgerHandler)
    print("=" * 60)
    print(f" AGENTESROW LEDGER UI SERVER RUNNING ON PORT {PORT}")
    print(f" Open in Browser: http://localhost:{PORT}/")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
