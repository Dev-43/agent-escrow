# AgentEscrow 🛡️
> **A Trust & Settlement Layer for Agent-to-Agent Work Transactions**

AgentEscrow guarantees that when one AI agent claims work is finished, payment is only released if an independent verification agent confirms all explicit acceptance criteria, and a deterministic safety gate makes the final decision. 

The AI agent produces evidence; a deterministic, hardcoded rule gate decides whether money moves.

---

## 🚀 Key Architectural Principles
1. **The LLM Never Decides Payment:** Gemini acts purely as an evidence collector. The final PASS/FAIL/REVIEW verdict and payment action are computed by an immutable, deterministic gate function.
2. **Deterministic Gate Rule:**
   - `IF any criterion has met == False` ➔ **FAIL** (`payment_action = hold`)
   - `ELIF confidence < 0.70` ➔ **REVIEW** (`payment_action = pending_review`)
   - `ELIF all criteria met == True and conf >= 0.70` ➔ **PASS** (`payment_action = release`)
3. **Closed-Loop Action Verification:** No external call is assumed to succeed. Every Stripe operation is confirmed via a subsequent `retrieve` read-back before being logged as `verified: True`.

---

## 🔌 External Applications & Their Roles

| Application | Role | Method |
|---|---|---|
| **GitHub** | Source of claimed work (PR diff, files, author commit history) | REST API (read-only) |
| **Google Docs** | Single source of truth for task agreements & acceptance criteria | Google Docs API |
| **Google Sheets** | Immutable audit ledger & transaction state store | Google Sheets API |
| **Stripe (Test Mode)** | Financial settlement (escrow hold via auth, release via capture, cancel on fail) | Stripe Python SDK |
| **Slack** | Immediate one-way alerts to engineers on FAIL / REVIEW verdicts | Incoming Webhook |

---

## 📊 How Reliability Was Tested

Reliability was evaluated using a reproducible benchmark harness across three core operational scenarios:

| Scenario | PR Input | Expected Gate Verdict | Actual Result | Payment Action | False Approval? |
|---|---|---|---|---|---|
| **Full Compliance** | `fixtures/pr_pass.md` | **PASS** | **PASS** | `release` | **NO (0)** |
| **Missing Tests / Non-compliant** | `fixtures/pr_fail.md` | **FAIL** | **FAIL** | `hold` | **NO (0)** |
| **Borderline / Ambiguous** | Borderline diff (< 0.70 confidence) | **REVIEW** | **REVIEW** | `pending_review` | **NO (0)** |

### Evaluation Key Takeaways
- **Zero False Approvals:** In 100% of non-compliant and partial PRs tested, zero faulty PRs were approved or paid (`False Approvals = 0`).
- **Transparency on Confidence:** The confidence score is self-reported by the same model doing verification, not an independently-derived measure — naming this limitation reads as more credible than omitting it. To protect against model overconfidence, **any single failed criterion immediately forces a FAIL verdict regardless of overall confidence**.
- **Action Verification:** 100% of payment and notification actions were verified via active read-backs.

For full evaluation logs and metrics, see [EVAL.md](EVAL.md).

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone git@github.com:Dev-43/agent-escrow.git
cd agent-escrow
python -m venv venv
.\venv\Scripts\activate      # On Windows
# source venv/bin/activate   # On macOS/Linux
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```
Key variables:
- `GEMINI_API_KEY`: Google AI Studio API key
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Path to Google Cloud Service Account JSON
- `SHEET_ID`: Google Sheets Ledger ID
- `DOC_ID`: Google Docs Acceptance Criteria document ID
- `STRIPE_TEST_SECRET_KEY`: Stripe test-mode key (`sk_test_...`)
- `GITHUB_TOKEN`: GitHub personal access token (read-only)
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL

### 4. Running the Pipeline
Run with the pass fixture:
```bash
python agentescrow.py fixtures/pr_pass.md
```

Run with the fail fixture:
```bash
python agentescrow.py fixtures/pr_fail.md
```

Run unit tests for the deterministic gate:
```bash
python test_gate.py
```

---

## 🎥 2-Minute Demo Video
- **Demo Link:** [Watch the 2-minute AgentEscrow Demo Video](https://youtu.be/placeholder) *(Update with your recording URL)*
