# AgentEscrow 🛡️
> **Autonomous Trust & Settlement Protocol for Agent-to-Agent Work Transactions**

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-agent--escrow.onrender.com-00f59b?style=flat-square)](https://agent-escrow.onrender.com/)
[![Reliability Benchmark](https://img.shields.io/badge/False%20Approvals-0%20(100%25%20Safety)-00f59b?style=flat-square)](#-how-reliability-was-tested)
[![External Apps](https://img.shields.io/badge/External%20Integrations-5%20Connected%20APIs-00f59b?style=flat-square)](#-external-applications--their-roles)
[![License: MIT](https://img.shields.io/badge/License-MIT-white?style=flat-square)](LICENSE)
[![Demo Video](https://img.shields.io/badge/Demo%20Video-YouTube%20%7C%20Drive-ff3b5c?style=flat-square)](#-2-minute-demo-video)

---

## 🌐 Live Interactive Cloud Deployment
- **Live Deployed App:** **[https://agent-escrow.onrender.com/](https://agent-escrow.onrender.com/)**
- *Zero setup required: Judges can test the real-time Gemini verification and Stripe settlement directly in their browser.*

---

## 🎥 2-Minute Demo Video
- **Primary (YouTube):** [Watch the AgentEscrow 2-Minute Demo on YouTube](https://youtu.be/Ys0rY0_XVZ0)
- **Mirror (Google Drive):** [Watch on Google Drive (Public Stream / Download)](https://drive.google.com/file/d/1VhBrrGV5Mn88IUfeCPP-yvDWCH6tR03c/view?usp=sharing)

---

## 💡 The Problem We Are Solving

In the emerging autonomous agent economy, AI agents can execute technical work for other agents — such as generating pull requests, fixing bugs, and deploying microservices. 

However, there is a fundamental **trust and settlement bottleneck**:
1. **The Claim vs. Truth Dilemma:** When Agent B claims work is complete and requests payment, how can Agent A reliably verify that all explicit acceptance criteria were met before money changes hands?
2. **The LLM Hallucination Risk:** If an LLM directly decides whether to release funds, model hallucinations, prompt injections, or stochastic overconfidence can lead to catastrophic financial drain.
3. **The Silent Failure Trap:** Most workflows assume external API calls succeed upon sending. Without closed-loop read-back verification, payments can be marked "released" while silently failing downstream.

### The AgentEscrow Solution
AgentEscrow separates **evidence collection** from **financial settlement**:
- **Gemini acts purely as an impartial inspector**, reading the agreement from Google Docs and extracting structured evidence from the GitHub pull request diff.
- **A hardcoded, deterministic rule gate makes the final call** — not the probabilistic model.
- **Every external financial action is closed-loop verified** with real read-backs before being marked complete in an immutable Google Sheets ledger.

```
┌──────────────┐         ┌──────────────┐         ┌─────────────────────────┐         ┌──────────────────────┐
│  Google Doc  │         │  GitHub PR   │         │       Gemini 2.5        │         │  Deterministic Gate  │
│  Agreement   │ ──────> │  Claimed Work│ ──────> │   Evidence Collector    │ ──────> │ IF any fail -> HOLD  │
│  (Criteria)  │         │  (Live Diff) │         │ (met: bool, confidence) │         │ ELIF conf<0.7->REVIEW│
└──────────────┘         └──────────────┘         └─────────────────────────┘         └──────────┬───────────┘
                                                                                                 │
                                      ┌──────────────────────────────────────────────────────────┴──────────┐
                                      ▼                                     ▼                               ▼
                           [ PASS: Release Funds ]                [ FAIL: Hold & Alert ]          [ REVIEW: Escalate ]
                           • Stripe: Capture Escrow               • Stripe: Cancel Escrow         • Stripe: Maintain Hold
                           • Verify: status=succeeded             • Verify: status=canceled       • Alert: Slack Notification
                           • Sheets: Append Row                   • Alert: Slack Channel          • Sheets: Append Row
```

---

## 🚀 Key Architectural Principles

1. **The LLM Never Decides Payment:** Gemini produces structured evidence and a confidence score. It has zero authority over funds.
2. **Deterministic Safety Gate:**
   ```text
   IF any criterion has met == False              -> FAIL   (payment_action = hold, cancel Stripe hold)
   ELIF confidence < 0.70                         -> REVIEW (payment_action = pending_review, escalate to human)
   ELIF all criteria met == True and conf >= 0.70 -> PASS   (payment_action = release, capture Stripe escrow)
   ```
3. **Closed-Loop Action Verification:** No API call is assumed to succeed. Every Stripe operation is confirmed via a subsequent `PaymentIntent.retrieve()` read-back before logging `verified: True`.
4. **No Intermediary Databases:** Google Sheets serves as the transparent, append-only transaction-state store and immutable audit ledger.

---

## 🔌 External Applications & Their Roles

AgentEscrow connects **5 distinct external applications** across a causal, non-redundant pipeline:

| Application | Role in Pipeline | Access Method |
|---|---|---|
| **Google Docs** | **Single Source of Truth** for task agreements and explicit acceptance criteria. | Google Docs REST API (OAuth2 Service Account) |
| **GitHub** | **Source of Claimed Work**: Fetches pull request diffs, changed files, and metadata. | GitHub REST API (Read-only Personal Access Token) |
| **Google Sheets** | **Immutable Audit Ledger**: Real-time transaction state store with verified timestamps and confidence ratings. | Google Sheets API v4 (Append-only) |
| **Stripe (Test Mode)** | **Financial Settlement**: Escrow hold via authorization, release via capture, or cancellation on fail. | Stripe Python SDK (Live read-back verified) |
| **Slack** | **Engineering Alerts**: Immediate notification to engineers on non-compliant PRs and human escalation requests. | Slack Incoming Webhooks |

---

## 📊 How Reliability Was Tested

Reliability was evaluated using a version-controlled benchmark harness ([`eval_harness.py`](eval_harness.py)) and documented in [`EVAL.md`](EVAL.md) across three operational scenarios:

| # | Scenario | Input Fixture | Criteria Evaluated | Expected Verdict | Actual Result | Payment Action | False Approval? |
|---|---|---|---|---|---|---|---|
| 1 | **Full Compliance** | `fixtures/pr_pass.md` | Token bucket limiter + full test suite + 0 unapproved deps | **PASS** | **PASS** | `release` | **NO (0)** ✅ |
| 2 | **Deficient / Missing Tests** | `fixtures/pr_fail.md` | Incomplete tests (TODO placeholder only) | **FAIL** | **FAIL** | `hold` | **NO (0)** ✅ |
| 3 | **Borderline / Ambiguous** | `fixtures/pr_pass.md` | Unverifiable concurrency & optimal latency claims | **REVIEW** | **REVIEW** | `pending_review` | **NO (0)** ✅ |

### Evaluation Key Takeaways
- **Zero False Approvals (`False Approvals = 0`):** In 100% of non-compliant test cases, bad work was never paid out.
- **Transparency on Model Confidence:** The confidence score is self-reported by the model doing verification. To protect against model overconfidence, **any single failed criterion immediately forces a FAIL verdict regardless of overall confidence**.
- **Live GitHub PR Confirmation:** The pipeline was tested against real, live GitHub pull requests ([PR #1](https://github.com/Dev-43/agent-escrow/pull/1) and [PR #2](https://github.com/Dev-43/agent-escrow/pull/2)), confirming real-world GitHub API diff retrieval, live Stripe test captures, and live Slack webhook pushes.

For full evaluation logs and metrics, see [EVAL.md](EVAL.md).

---

## 🛠️ Step-by-Step Guide for Judges (Run Locally in 60 Seconds)

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Quick Setup
Clone the repository and install the dependencies:
```bash
git clone https://github.com/Dev-43/agent-escrow.git
cd agent-escrow
python -m venv venv
.\venv\Scripts\activate      # On Windows
# source venv/bin/activate   # On macOS/Linux
pip install -r requirements.txt
```

---

### Option 0: Test the Live Cloud Dashboard (Zero Setup Required!)
Judges can immediately run and inspect the end-to-end verification pipeline in the cloud:
👉 **[https://agent-escrow.onrender.com/](https://agent-escrow.onrender.com/)**

- Click **Verify PR #1 (PASS)**: Observe Gemini extracting evidence, the deterministic gate checking criteria, and Stripe capturing escrow funds live.
- Click **Verify PR #2 (FAIL)**: Watch the gate catch incomplete unit tests and hold payment safely.
- Click **Ambiguous (REVIEW)**: Watch the gate drop confidence below 0.70 and halt payment for human escalation.

---

### Option A: Run the Deterministic Gate Unit Tests (Instant, No API Keys Required)
Verify the core safety logic that guards payment actions:
```bash
python test_gate.py
```
*Expected Output:*
```text
test_borderline_low_confidence_routes_to_review ... ok
test_clear_fail_routes_to_hold ... ok
test_clear_pass_routes_to_release ... ok
test_failed_criterion_with_high_confidence_routes_to_fail ... ok
Ran 4 tests in 0.001s - OK
```

---

### Option B: Run the Evaluation Benchmark Suite
Run the 3 canonical benchmark scenarios (verdict accuracy + 0 false approvals):
```bash
python eval_harness.py
```

---

### Option C: Launch the Interactive True Black Web Dashboard
Launch the local fintech console on your machine:
```bash
python serve_ledger.py
```
Open **[http://localhost:5000/](http://localhost:5000/)** in your browser.
- Click **Verify PR #1 (PASS)** to watch the 6-stage stepper execute and capture payment.
- Click **Verify PR #2 (FAIL)** to watch the safety gate catch missing tests and hold payment.
- Click **Ambiguous (REVIEW)** to see the system hold and escalate when confidence falls below 0.70.

---

### Option D: Run Live Verification via CLI against Real GitHub PRs
Configure your credentials in `.env`:
```bash
cp .env.example .env
# Fill in GEMINI_API_KEY, STRIPE_TEST_SECRET_KEY, GITHUB_TOKEN, etc.
```

Run live against **Pull Request #1 (PASS case)**:
```bash
python agentescrow.py fixtures/pr_pass.md
```

Run live against **Pull Request #2 (FAIL case - missing unit tests)**:
```bash
python agentescrow.py fixtures/pr_fail.md
```

---

## 📁 Repository Structure

```text
├── agentescrow.py          # Core pipeline: context collection, verification, gate, settlement & logging
├── eval_harness.py         # Automated reliability evaluation benchmark (3 scenarios)
├── test_gate.py            # Unit test suite for the deterministic safety gate rule
├── serve_ledger.py         # Production HTTP server serving the interactive fintech web console
├── frontend/
│   └── ledger.html         # True Black interactive dashboard with live 6-stage pipeline stepper
├── fixtures/
│   ├── pr_pass.md          # Fixture: Compliant pull request with full test coverage
│   ├── pr_fail.md          # Fixture: Non-compliant pull request missing unit tests
│   └── pr_ambiguous.md     # Fixture: Borderline pull request with subjective criteria
├── EVAL.md                 # Detailed evaluation methodology, scenario logs, and metrics
├── Procfile                # Render cloud deployment process definition
├── render.yaml             # Infrastructure-as-Code blueprint specification
├── runtime.txt             # Python runtime specification (python-3.11.9)
├── LICENSE                 # MIT License
├── requirements.txt        # Pinned project dependencies
└── .env.example            # Template for required environment variables
```

---

## ⚖️ License
Released under the [MIT License](LICENSE). Copyright (c) 2026 Devesh Laxman Dolas.
