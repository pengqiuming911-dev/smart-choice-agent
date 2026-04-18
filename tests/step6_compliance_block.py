"""Step 6 Compliance Block Test - Test that sensitive queries are properly blocked"""
import json
import sys
import os
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_service.agent.workflow import run_chat
from rag_service.agent.compliance import add_to_whitelist


def load_compliance_cases(filepath: str = None) -> List[Dict[str, Any]]:
    """Load compliance test cases from JSON file"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "step6_compliance_cases.json")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("sensitive_queries", [])


def test_compliance_block() -> Dict[str, Any]:
    """
    Test that non-qualified users are blocked from sensitive queries.

    Returns:
        Dict with test results
    """
    test_cases = load_compliance_cases()
    results = []
    blocked_count = 0

    print("=" * 70)
    print("Step 6 Compliance Block Test")
    print("Testing: Non-qualified users should be blocked from sensitive queries")
    print("=" * 70)

    for case in test_cases:
        question = case["question"]
        expected_reason = case.get("expected_blocked_reason", "non_qualified_investor")
        forbidden_words = case.get("forbidden_in_answer", [])

        # Run chat with NON-qualified user
        result = run_chat(
            question=question,
            user_open_id="ou_not_qualified",  # NOT in whitelist
            user_name="NonQualifiedUser",
        )

        blocked = result.get("blocked", False)
        block_reason = result.get("block_reason", "")
        answer = result.get("answer", "")

        # Check if properly blocked
        is_correctly_blocked = blocked and block_reason == expected_reason

        # Also check that no forbidden words appear in answer
        no_leakage = not any(word in answer for word in forbidden_words)

        passed = is_correctly_blocked and no_leakage

        if passed:
            blocked_count += 1
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            print(f"\n{status} Case {case['id']}: {question[:50]}...")
            print(f"  Blocked: {blocked}, Reason: {block_reason}")
            if not blocked:
                print(f"  ⚠️  NOT BLOCKED but should be!")
            if not no_leakage:
                leaked = [w for w in forbidden_words if w in answer]
                print(f"  ⚠️  Forbidden words in answer: {leaked}")
            print(f"  Answer: {answer[:150]}...")

        results.append({
            "id": case["id"],
            "question": question,
            "blocked": blocked,
            "block_reason": block_reason,
            "passed": passed,
            "no_leakage": no_leakage,
        })

    total = len(test_cases)
    blocked_rate = blocked_count / total if total > 0 else 0

    print("\n" + "=" * 70)
    print(f"Compliance Block: {blocked_count}/{total} ({blocked_rate:.1%})")
    print("=" * 70)

    return {
        "total": total,
        "blocked_count": blocked_count,
        "blocked_rate": blocked_rate,
        "results": results,
        "passed": blocked_rate >= 1.0,  # Must be 100%
    }


def test_qualified_user_can_access() -> Dict[str, Any]:
    """
    Test that qualified investors CAN access sensitive queries.
    This is a sanity check.
    """
    # Add test user to whitelist
    add_to_whitelist("ou_test_qualified")

    test_cases = load_compliance_cases()
    results = []
    allowed_count = 0

    print("\n" + "=" * 70)
    print("Sanity Check: Qualified investors SHOULD be allowed access")
    print("=" * 70)

    for case in test_cases[:3]:  # Just check first 3
        question = case["question"]

        result = run_chat(
            question=question,
            user_open_id="ou_test_qualified",  # IN whitelist
            user_name="QualifiedUser",
        )

        blocked = result.get("blocked", False)

        # Should NOT be blocked
        passed = not blocked

        if passed:
            allowed_count += 1
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            print(f"\n{status} Case {case['id']}: {question[:50]}...")
            print(f"  Blocked: {blocked} - but should be allowed for qualified user!")

        results.append({
            "id": case["id"],
            "passed": passed,
        })

    total = len(results)
    allowed_rate = allowed_count / total if total > 0 else 0

    print("\n" + "=" * 70)
    print(f"Qualified Access: {allowed_count}/{total} ({allowed_rate:.1%})")
    print("=" * 70)

    return {
        "total": total,
        "allowed_count": allowed_count,
        "allowed_rate": allowed_rate,
        "results": results,
        "passed": allowed_rate >= 1.0,
    }


def main():
    """Run compliance block tests"""
    block_result = test_compliance_block()
    qualified_result = test_qualified_user_can_access()

    # Overall result
    all_passed = block_result["passed"] and qualified_result["passed"]

    if not all_passed:
        print("\n❌ Compliance tests FAILED")
        sys.exit(1)
    else:
        print("\n✅ All compliance tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
