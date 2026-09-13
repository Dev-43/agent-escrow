# EVAL.md — Reliability Evaluation Harness & Benchmark Results

## Objective
Evaluate the AgentEscrow trust layer across key transactional scenarios to measure:
- **Verdict Accuracy** (Target: 3/3, 100%)
- **False Approvals (Critical Hazardous Failure Mode)**: **0** (A faulty or non-compliant PR must NEVER trigger payment release)
- **Deterministic Routing**: Ensure the deterministic gate logic strictly enforces rules without LLM hallucination in payment actions.

---

## Benchmark Scenarios & Results

| # | Scenario | Input Fixture | Criteria Evaluated | Expected Verdict | Actual Verdict | Confidence | Payment Action | False Approval? |
|---|---|---|---|---|---|---|---|---|
| 1 | **Full Compliance** | `fixtures/pr_pass.md` | Standard Criteria (Rate limiter + full test suite + zero unapproved dependencies) | **PASS** | **PASS** | `0.95` | `release` | **NO (0)** ✅ |
| 2 | **Deficient / Missing Tests** | `fixtures/pr_fail.md` | Standard Criteria (Incomplete tests, TODO placeholder only) | **FAIL** | **FAIL** | `0.95` | `hold` | **NO (0)** ✅ |
| 3 | **Borderline / Subjective Criteria** | `fixtures/pr_pass.md` | Unverifiable concurrency & optimal latency claims without benchmarks | **REVIEW** | **REVIEW** | `0.60` | `pending_review` | **NO (0)** ✅ |

---

## Summary Metrics
- **Total Scenarios Evaluated:** 3
- **Verdict Accuracy:** **100% (3/3)**
- **False Approvals (Critical Failure Mode):** **0 (TARGET: 0)**
- **False Rejections:** 0
- **Action Verification Success Rate:** 100% (All payment actions verified via retrieve read-back)

---

## Reliability Disclosure & Architectural Guarantees
1. **Separation of Evidence and Settlement:** The LLM produces evidence and a self-reported confidence score; it is strictly prohibited from touching payment actions. The deterministic gate rule enforces final verdicts.
2. **Self-Reported Confidence Disclosure:** The confidence score is self-reported by the model during verification. To eliminate reliance on model overconfidence:
   - Any single failed criterion immediately forces **FAIL**, bypassing confidence scoring entirely.
   - Any subjective or unverifiable criterion scores below 0.70 confidence, forcing **REVIEW** to a human operator.
3. **Closed-Loop Action Verification:** External actions (Stripe captures/cancellations, Sheets audit logging, Slack webhook delivery) are followed by active read-backs before being marked `verified: True`.

---

## How to Reproduce
Run the automated evaluation benchmark:
```bash
python eval_harness.py
```
