import os
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

print("=" * 60)
print(" AGENTESROW: CREDENTIAL VERIFICATION SUITE")
print("=" * 60)

# 1. Test Stripe Test Mode
stripe_key = os.getenv("STRIPE_TEST_SECRET_KEY")
print("\n[1/5] Testing Stripe Test Mode...")
if stripe_key and stripe_key.startswith("sk_test_"):
    try:
        import stripe
        stripe.api_key = stripe_key
        # Create test hold
        intent = stripe.PaymentIntent.create(
            amount=5000,
            currency="usd",
            capture_method="manual",
            description="Escrow Test Hold",
            payment_method_types=["card"]
        )
        print(f"      ✅ Created PaymentIntent: {intent.id} (Status: {intent.status})")
        # Cancel test hold
        canceled = stripe.PaymentIntent.cancel(intent.id)
        print(f"      ✅ Canceled PaymentIntent: {canceled.id} (Status: {canceled.status})")
        print("      🌟 Stripe Integration: 100% OPERATIONAL")
    except Exception as e:
        print(f"      ❌ Stripe Error: {e}")
else:
    print("      ⚠️ Stripe Key missing or not in test mode.")

# 2. Test GitHub Token
gh_token = os.getenv("GITHUB_TOKEN")
print("\n[2/5] Testing GitHub Token...")
if gh_token and gh_token.startswith("ghp_"):
    try:
        import requests
        headers = {"Authorization": f"Bearer {gh_token}", "User-Agent": "AgentEscrow-Check"}
        res = requests.get("https://api.github.com/user", headers=headers, timeout=5)
        if res.status_code == 200:
            user_data = res.json()
            print(f"      ✅ GitHub Authenticated as: {user_data.get('login')} ({user_data.get('name')})")
            print("      🌟 GitHub Integration: 100% OPERATIONAL")
        else:
            print(f"      ❌ GitHub returned {res.status_code}: {res.text}")
    except Exception as e:
        print(f"      ❌ GitHub Request Error: {e}")
else:
    print("      ⚠️ GitHub Token missing or invalid prefix.")

# 3. Test Slack Incoming Webhook
slack_url = os.getenv("SLACK_WEBHOOK_URL")
print("\n[3/5] Testing Slack Incoming Webhook...")
if slack_url and slack_url.startswith("https://hooks.slack.com"):
    try:
        import requests
        payload = {"text": "🛡️ *AgentEscrow Integration Test*: Slack incoming webhook is connected and working successfully!"}
        res = requests.post(slack_url, json=payload, timeout=5)
        if res.status_code == 200 and res.text == "ok":
            print("      ✅ Slack message delivered successfully! (HTTP 200: ok)")
            print("      🌟 Slack Integration: 100% OPERATIONAL")
        else:
            print(f"      ❌ Slack returned {res.status_code}: {res.text}")
    except Exception as e:
        print(f"      ❌ Slack Request Error: {e}")
else:
    print("      ⚠️ Slack Webhook URL missing or invalid format.")

# 4. Test Google Cloud Service Account
sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service-account.json")
print("\n[4/5] Testing Google Cloud Service Account...")
if os.path.exists(sa_path):
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        creds = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/documents.readonly"]
        )
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
        print(f"      ✅ Service Account Verified: {creds.service_account_email}")
        print("      🌟 Google Cloud Auth: 100% OPERATIONAL")
    except Exception as e:
        print(f"      ❌ Service Account Error: {e}")
else:
    print(f"      ⚠️ Service Account file not found at: {sa_path}")

# 5. Test Gemini API
gemini_key = os.getenv("GEMINI_API_KEY")
print("\n[5/5] Testing Gemini API...")
if gemini_key:
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content("Respond with exactly: OK")
        print(f"      ✅ Gemini Response: {resp.text.strip()}")
        print("      🌟 Gemini API: 100% OPERATIONAL")
    except Exception as e:
        print(f"      ❌ Gemini API Error: {e}")
else:
    print("      ⚠️ Gemini API Key missing.")

print("\n" + "=" * 60)
print(" VERIFICATION COMPLETE")
print("=" * 60)
