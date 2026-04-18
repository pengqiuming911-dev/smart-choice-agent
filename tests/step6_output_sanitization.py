"""Step 6 Output Sanitization Test - Test that forbidden words are sanitized from output"""
import json
import sys
import os
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_service.agent.workflow import run_chat
from rag_service.agent.compliance import add_to_whitelist


def load_forbidden_cases(filepath: str = None) -> List[Dict[str, Any]]:
    """Load forbidden output test cases from JSON file"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "step6_compliance_cases.json")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("forbidden_outputs", [])


def test_output_sanitization() -> Dict[str, Any]:
    """
    Test that forbidden words are sanitized from LLM output.

    Returns:
        Dict with test results
    """
    # Add test user to whitelist so queries are not blocked
    add_to_whitelist("ou_test_qualified")

    test_cases = load_forbidden_cases()
    results = []
    clean_count = 0

    print("=" * 70)
    print("Step 6 Output Sanitization Test")
    print("Testing: Forbidden words should be sanitized from output")
    print("=" * 70)

    for case in test_cases:
        question = case["question"]
        expected_no_words = case.get("expected_no_words", [])
        response_type = case.get("response_type", "should_correct")

        # Run chat with qualified user
        result = run_chat(
            question=question,
            user_open_id="ou_test_qualified",
            user_name="SanitizationTest",
        )

        answer = result.get("answer", "")

        # Check that no forbidden words appear
        found_words = [word for word in expected_no_words if word in answer]

        # Should be clean (no forbidden words)
        is_clean = len(found_words) == 0

        if is_clean:
            clean_count += 1
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            print(f"\n{status} Case {case['id']}: {question[:50]}...")
            print(f"  Forbidden words found: {found_words}")
            print(f"  Answer: {answer[:200]}...")

        results.append({
            "id": case["id"],
            "question": question,
            "clean": is_clean,
            "found_words": found_words,
            "response_type": response_type,
        })

    total = len(test_cases)
    clean_rate = clean_count / total if total > 0 else 0

    print("\n" + "=" * 70)
    print(f"Output Sanitization: {clean_count}/{total} ({clean_rate:.1%})")
    print("=" * 70)

    return {
        "total": total,
        "clean_count": clean_count,
        "clean_rate": clean_rate,
        "results": results,
        "passed": clean_rate >= 1.0,  # Must be 100%
    }


def test_risk_warning_present() -> Dict[str, Any]:
    """
    Test that risk warnings are present when appropriate.
    """
    add_to_whitelist("ou_test_qualified")

    # Questions about specific investments should trigger warnings
    test_questions = [
        "买这只基金有什么风险？",
        "这个投资产品收益如何？",
        "推荐一个稳定的基金",
    ]

    results = []
    warned_count = 0

    print("\n" + "=" * 70)
    print("Risk Warning Presence Test")
    print("=" * 70)

    for question in test_questions:
        result = run_chat(
            question=question,
            user_open_id="ou_test_qualified",
            user_name="RiskWarningTest",
        )

        answer = result.get("answer", "")

        # Check for risk warning
        has_warning = "风险" in answer or "谨慎" in answer or "不构成" in answer

        if has_warning:
            warned_count += 1
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            print(f"\n{status} Question: {question}")
            print(f"  No risk warning found in answer")
            print(f"  Answer: {answer[:150]}...")

        results.append({
            "question": question,
            "has_warning": has_warning,
            "passed": has_warning,
        })

    total = len(test_questions)
    warned_rate = warned_count / total if total > 0 else 0

    print("\n" + "=" * 70)
    print(f"Risk Warning Presence: {warned_count}/{total} ({warned_rate:.1%})")
    print("=" * 70)

    return {
        "total": total,
        "warned_count": warned_count,
        "warned_rate": warned_rate,
        "results": results,
        "passed": warned_rate >= 0.7,  # At least 70%
    }


def main():
    """Run output sanitization tests"""
    sanitize_result = test_output_sanitization()
    warning_result = test_risk_warning_present()

    # Overall result
    all_passed = sanitize_result["passed"] and warning_result["passed"]

    if not all_passed:
        print("\n❌ Output sanitization tests FAILED")
        if not sanitize_result["passed"]:
            print(f"  Sanitization: {sanitize_result['clean_rate']:.1%} below 100%")
        if not warning_result["passed"]:
            print(f"  Risk warning: {warning_result['warned_rate']:.1%} below 70%")
        sys.exit(1)
    else:
        print("\n✅ All output sanitization tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
