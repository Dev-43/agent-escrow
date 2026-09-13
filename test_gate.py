import unittest
from typing import TypedDict, Literal

class Evidence(TypedDict):
    criterion: str
    met: bool
    evidence_text: str

class VerificationResult(TypedDict):
    task_id: str
    evidence: list[Evidence]
    confidence: float
    raw_reasoning: str

class GateDecision(TypedDict):
    task_id: str
    verdict: Literal["PASS", "FAIL", "REVIEW"]
    reason: str
    payment_action: Literal["release", "hold", "pending_review"]

def deterministic_gate(result: VerificationResult) -> GateDecision:
    """
    Deterministic gate rule (fixed - not LLM-decided):
    IF any criterion has met == False        -> FAIL, payment_action = hold
    ELIF confidence < 0.7                     -> REVIEW, payment_action = pending_review
    ELIF all criteria met == True and conf >= 0.7 -> PASS, payment_action = release
    """
    task_id = result.get("task_id", "")
    evidence = result.get("evidence", [])
    confidence = float(result.get("confidence", 0.0))

    if any(not ev.get("met", False) for ev in evidence):
        failed = [ev.get("criterion", "") for ev in evidence if not ev.get("met", False)]
        return {
            "task_id": task_id,
            "verdict": "FAIL",
            "reason": f"Criteria failed: {', '.join(failed)}",
            "payment_action": "hold",
        }
    elif confidence < 0.7:
        return {
            "task_id": task_id,
            "verdict": "REVIEW",
            "reason": f"Confidence {confidence:.2f} is below 0.70 threshold",
            "payment_action": "pending_review",
        }
    else:
        return {
            "task_id": task_id,
            "verdict": "PASS",
            "reason": f"All criteria met with confidence {confidence:.2f} >= 0.70",
            "payment_action": "release",
        }

class TestDeterministicGate(unittest.TestCase):
    def test_clear_pass(self):
        result: VerificationResult = {
            "task_id": "task_pass_01",
            "evidence": [
                {"criterion": "Rate limiter implemented", "met": True, "evidence_text": "Found in rate_limiter.py"},
                {"criterion": "Unit tests included", "met": True, "evidence_text": "Found in test_rate_limiter.py"},
            ],
            "confidence": 0.95,
            "raw_reasoning": "Both criteria are fully satisfied.",
        }
        decision = deterministic_gate(result)
        self.assertEqual(decision["verdict"], "PASS")
        self.assertEqual(decision["payment_action"], "release")

    def test_clear_fail(self):
        result: VerificationResult = {
            "task_id": "task_fail_01",
            "evidence": [
                {"criterion": "Rate limiter implemented", "met": True, "evidence_text": "Found in rate_limiter.py"},
                {"criterion": "Unit tests included", "met": False, "evidence_text": "Tests only contain TODO comment"},
            ],
            "confidence": 0.90,
            "raw_reasoning": "Unit tests criterion failed.",
        }
        decision = deterministic_gate(result)
        self.assertEqual(decision["verdict"], "FAIL")
        self.assertEqual(decision["payment_action"], "hold")

    def test_low_confidence_review(self):
        result: VerificationResult = {
            "task_id": "task_review_01",
            "evidence": [
                {"criterion": "Rate limiter implemented", "met": True, "evidence_text": "Code present but ambiguous"},
                {"criterion": "Unit tests included", "met": True, "evidence_text": "Minimal test case"},
            ],
            "confidence": 0.65,
            "raw_reasoning": "Criteria appear met but implementation is borderline.",
        }
        decision = deterministic_gate(result)
        self.assertEqual(decision["verdict"], "REVIEW")
        self.assertEqual(decision["payment_action"], "pending_review")

if __name__ == "__main__":
    unittest.main()
