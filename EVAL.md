# EVAL.md — Reliability Evaluation Harness & Benchmark Results

## Objective
Evaluate the AgentEscrow trust layer across key transactional scenarios to measure:
- **Verdict Accuracy** (Target: 3/3, 100%)
- **False Approvals (False Positive / Hazardous Failure Mode)**: **0** (A faulty or incomplete PR must NEVER trigger payment release)
- **Deterministic Routing**: Ensure the deterministic gate logic strictly enforces rules without LLM hallucination in payment actions.

---

## Benchmark Scenarios & Results

| # | Scenario | Input | Expected Verdict | Actual Verdict | Payment Action | False Approval? | Notes |
|---|----------|-------|------------------|----------------|----------------|-----------------|-------|
| 1 | Full Compliance | `fixtures/pr_pass.md` | **PASS** | **PASS** | `release` | **NO (0)** | Rate limiter and comprehensive test suite verified |
| 2 | Missing Unit Tests | `fixtures/pr_fail.md` | **FAIL** | **FAIL** | `hold` | **NO (0)** | Incomplete tests caught, alert sent to Slack, funds held |
| 3 | Ambiguous Implementation | Borderline confidence (< 0.70) | **REVIEW** | **REVIEW** | `pending_review` | **NO (0)** | Below 0.70 threshold routed to human reviewer |

### Summary Metrics
- **Total Evaluated Scenarios:** 3
- **Verdict Accuracy:** 100% (3/3)
- **False Approvals (Critical Failure Mode):** **0**
- **False Rejections:** 0
- **Action Verification Success Rate:** 100% (All payment actions verified via retrieve read-back)

---

## Reliability Disclosure & Architectural Guarantee
1. **Separation of Evidence and Settlement:** The LLM produces evidence and a self-reported confidence score; it is strictly prohibited from touching payment actions. The deterministic gate rule enforces final verdicts.
2. **Self-Reported Confidence Disclosure:** The confidence score is self-reported by the model during verification. To eliminate reliance on model overconfidence, any failed criterion immediately triggers `FAIL`, bypassing confidence scoring.
3. **Closed-Loop Action Verification:** External actions (Stripe captures/cancellations, Sheets audit logging, Slack webhook delivery) are followed by read-backs before being marked `verified: True`.
