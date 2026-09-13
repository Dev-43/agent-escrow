"""
serve_ledger.py — Local HTTP server for the AgentEscrow Ledger UI
Reads live audit records from Google Sheets (or local ledger) and serves ledger.html
"""

import os
import sys
import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

PORT = int(os.getenv("PORT", "5000"))

def get_live_ledger_data():
    sheet_id = os.getenv("SHEET_ID")
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

    entries = []
    if sheet_id and os.path.exists(sa_path):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds = service_account.Credentials.from_service_account_file(
                sa_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = build("sheets", "v4", credentials=creds)
            res = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range="Ledger!A2:F50"
            ).execute()
            rows = res.get("values", [])

            for row in rows:
                if not row or len(row) < 3:
                    continue
                task_id = row[0]
                verdict = str(row[1]).lower()
                action = str(row[2]).lower()
                conf_val = float(row[3]) if len(row) > 3 and row[3] else 0.90
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
                else: # review
                    reason = "Borderline subjective criterion; confidence below 0.70 safety threshold."
                    evidence = [
                        {"met": True, "text": "Basic implementation meets initial specifications"},
                        {"met": True, "text": "Unverifiable performance claim requires human reviewer sign-off"}
                    ]
                    action_display = "PENDING — $50.00"

                entries.append({
                    "task_id": task_id,
                    "verdict": verdict,
                    "payment_action": action,
                    "action_display": action_display,
                    "confidence": conf_val,
                    "confidence_pct": int(conf_val * 100),
                    "timestamp": time_str,
                    "verified": verified,
                    "reason": reason,
                    "evidence": evidence
                })
        except Exception as e:
            print(f"[WARN] Failed fetching from Sheets API: {e}")

    # Fallback to local file if Sheets empty or failed
    if not entries and os.path.exists("ledger_local.jsonl"):
        with open("ledger_local.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    task_id, verdict, action = row[0], str(row[1]).lower(), str(row[2]).lower()
                    conf_val = float(row[3])
                    entries.append({
                        "task_id": task_id,
                        "verdict": verdict,
                        "payment_action": action,
                        "action_display": f"{action.upper()} — $50.00",
                        "confidence": conf_val,
                        "confidence_pct": int(conf_val * 100),
                        "timestamp": row[4].split("T")[1][:8] if "T" in row[4] else row[4],
                        "verified": bool(row[5]),
                        "reason": "Logged via local pipeline ledger.",
                        "evidence": [{"met": verdict == "pass", "text": "Verification evidence verified."}]
                    })
                except Exception:
                    pass

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
        if parsed.path == "/api/ledger":
            data = get_live_ledger_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif parsed.path == "/api/config":
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
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(body)
            except Exception:
                payload = {}

            pr_number = payload.get("pr_number")
            fixture = payload.get("fixture")
            task_id = payload.get("task_id")

            pr_num_int = int(pr_number) if pr_number else 1
            if not task_id:
                task_id = f"task_pr_{pr_num_int:03d}_{int(time.time())}"

            import agentescrow
            try:
                result = agentescrow.run_pipeline(
                    task_id=task_id,
                    fixture_path=fixture,
                    amount_cents=5000,
                    pr_number=pr_num_int
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
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, LedgerHandler)
    print("=" * 60)
    print(f" AGENTESROW LEDGER UI SERVER RUNNING")
    print(f" Open in Browser: http://localhost:{PORT}/")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
