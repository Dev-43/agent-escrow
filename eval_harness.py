"""
eval_harness.py — Automated Reliability Benchmark Suite for AgentEscrow
Runs the 3 canonical evaluation scenarios specified in BUILD.md and BUILD_solo.md:
1. Full Compliance (pr_pass.md) -> Expect PASS (release)
2. Deficient / Missing Tests (pr_fail.md) -> Expect FAIL (hold)
3. Ambiguous / Subjective Criteria -> Expect REVIEW (pending_review)

Guarantees & Metrics:
- Verdict Accuracy (Target: 3/3, 100%)
- False Approvals = 0 (No non-compliant PR ever triggers payment release)
"""

import os
import sys
import json
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from agentescrow import (
    TaskAgreement,
    VerificationResult,
    GateDecision,
    deterministic_gate,
    run_verification_agent,
    execute_stripe_action,
    execute_slack_notification,
    append_ledger_entry,
    fetch_acceptance_criteria,
    fetch_pr_content,
)

def run_evaluation_scenario(
    scenario_name: str,
    task_id: str,
    fixture_path: str,
    override_criteria: List[str] = None,
    expected_verdict: str = "PASS"
) -> Dict[str, Any]:
    print(f"\n" + "-" * 65)
    print(f" EVAL RUNNING: [{scenario_name}] (Task: {task_id})")
    print("-" * 65)

    # 1. Load Criteria
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    doc_id = os.getenv("DOC_ID")
    if override_criteria:
        criteria = override_criteria
    else:
        criteria = fetch_acceptance_criteria(doc_id, sa_json)

    agreement: TaskAgreement = {
        "task_id": task_id,
        "acceptance_criteria": criteria,
        "payment_amount_cents": 5000,
        "repo": os.getenv("GITHUB_REPO", "owner/repo"),
        "pr_number": 42,
    }

    # 2. Read Fixture PR Content
    pr_content = fetch_pr_content("", 0, None, fixture_path=fixture_path)

    # 3. Run Verification Agent
    gemini_key = os.getenv("GEMINI_API_KEY")
    t0 = time.time()
    verification = run_verification_agent(agreement, pr_content, gemini_key)
    latency = time.time() - t0

    # 4. Run Deterministic Gate
    decision = deterministic_gate(verification)

    # 5. External Actions with Verification
    stripe_key = os.getenv("STRIPE_TEST_SECRET_KEY")
    stripe_log = execute_stripe_action(decision, 5000, stripe_key)

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    slack_log = execute_slack_notification(decision, verification, slack_webhook)

    sheet_id = os.getenv("SHEET_ID")
    sheet_log = append_ledger_entry(decision, verification["confidence"], sheet_id, sa_json, stripe_log["verified"])

    is_correct = (decision["verdict"] == expected_verdict)
    is_false_approval = (expected_verdict != "PASS" and decision["verdict"] == "PASS")

    print(f"      Result: {decision['verdict']} (Expected: {expected_verdict}) | Correct: {'✅' if is_correct else '❌'}")
    print(f"      Confidence: {verification['confidence']:.2f} | Gate Rule: {decision['reason']}")
    print(f"      Payment Action: {decision['payment_action']} | Stripe Verified: {stripe_log['verified']}")

    return {
        "scenario": scenario_name,
        "task_id": task_id,
        "fixture": fixture_path,
        "expected": expected_verdict,
        "verdict": decision["verdict"],
        "confidence": verification["confidence"],
        "payment_action": decision["payment_action"],
        "correct": is_correct,
        "false_approval": is_false_approval,
        "latency_sec": round(latency, 2),
    }

def main():
    print("=" * 65)
    print(" AGENTESROW: AUTOMATED RELIABILITY EVALUATION HARNESS")
    print("=" * 65)

    scenarios = [
        {
            "name": "Scenario 1: Full Compliance",
            "task_id": "eval_pass_001",
            "fixture": "fixtures/pr_pass.md",
            "expected": "PASS",
            "override_criteria": None
        },
        {
            "name": "Scenario 2: Deficient / Missing Tests",
            "task_id": "eval_fail_002",
            "fixture": "fixtures/pr_fail.md",
            "expected": "FAIL",
            "override_criteria": None
        },
        {
            "name": "Scenario 3: Borderline / Subjective Criteria",
            "task_id": "eval_review_003",
            "fixture": "fixtures/pr_pass.md",
            "expected": "REVIEW",
            "override_criteria": [
                "Implement a TokenBucketRateLimiter class with configurable capacity",
                "Enforce rate limit middleware or decorator returning HTTP 429",
                "Ensure architecture adheres to enterprise-grade microservice concurrency norms and optimal latency trade-offs",
            ]
        }
    ]

    results = []
    for sc in scenarios:
        res = run_evaluation_scenario(
            scenario_name=sc["name"],
            task_id=sc["task_id"],
            fixture_path=sc["fixture"],
            override_criteria=sc.get("override_criteria"),
            expected_verdict=sc["expected"]
        )
        results.append(res)

    print("\n" + "=" * 65)
    print(" EVALUATION BENCHMARK SUMMARY")
    print("=" * 65)

    total = len(results)
    correct_count = sum(1 for r in results if r["correct"])
    false_approvals = sum(1 for r in results if r["false_approval"])
    accuracy = (correct_count / total) * 100

    print(f"\nTotal Scenarios Evaluated: {total}")
    print(f"Accuracy: {accuracy:.1f}% ({correct_count}/{total})")
    print(f"CRITICAL METRIC - False Approvals: {false_approvals} (TARGET: 0)")

    print("\n| Scenario | Expected | Actual | Payment Action | Conf | Correct | False Approval? |")
    print("|---|---|---|---|---|---|---|")
    for r in results:
        status_icon = "YES" if r["correct"] else "NO"
        fa_icon = "YES ❌" if r["false_approval"] else "NO (0) ✅"
        print(f"| {r['scenario'][:25]} | {r['expected']} | {r['verdict']} | {r['payment_action']} | {r['confidence']:.2f} | {status_icon} | {fa_icon} |")

    # Assert critical safety constraint
    assert false_approvals == 0, "SAFETY VIOLATION: False approval detected!"
    print("\n✅ EVALUATION HARNESS PASSED: 0 False Approvals confirmed across all test cases.")

if __name__ == "__main__":
    main()
