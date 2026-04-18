"""Step 6 Accuracy Test - Test answer accuracy using Step 3 test questions"""
import json
import sys
import os
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_service.agent.workflow import run_chat


def load_test_cases(filepath: str = None) -> List[Dict[str, Any]]:
    """Load test cases from JSON file"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "step6_compliance_cases.json")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Return normal_queries for accuracy testing
    return data.get("normal_queries", [])


def test_answer_accuracy(test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Test answer accuracy against must_contain_keywords.

    Args:
        test_cases: List of test cases with questions and expected keywords

    Returns:
        Dict with test results
    """
    results = []
    correct = 0

    print("=" * 70)
    print("Step 6 Accuracy Test")
    print("=" * 70)

    for case in test_cases:
        question = case["question"]
        must_keywords = case.get("must_contain_keywords", [])

        # Run chat with qualified investor (to bypass compliance for normal queries)
        result = run_chat(
            question=question,
            user_open_id="ou_test_qualified",  # Whitelisted user
            user_name="AccuracyTest",
        )

        # Check if answer contains required keywords
        answer = result.get("answer", "")
        keywords_found = [kw for kw in must_keywords if kw in answer]

        is_correct = len(keywords_found) == len(must_keywords)

        if is_correct:
            correct += 1
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            missing = set(must_keywords) - set(keywords_found)
            print(f"\n{status} Case {case['id']}: {question[:50]}...")
            print(f"  Missing keywords: {missing}")
            print(f"  Answer: {answer[:200]}...")

        results.append({
            "id": case["id"],
            "question": question,
            "correct": is_correct,
            "keywords_found": keywords_found,
            "missing_keywords": list(set(must_keywords) - set(keywords_found)),
            "answer_preview": answer[:100],
        })

    total = len(test_cases)
    accuracy = correct / total if total > 0 else 0

    print("\n" + "=" * 70)
    print(f"Accuracy: {correct}/{total} ({accuracy:.1%})")
    print("=" * 70)

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "results": results,
        "passed": accuracy >= 0.75,
    }


def main():
    """Run accuracy tests"""
    test_cases = load_test_cases()
    result = test_answer_accuracy(test_cases)

    # Exit with error code if test failed
    if not result["passed"]:
        print(f"\n❌ Test failed: accuracy {result['accuracy']:.1%} below threshold 75%")
        sys.exit(1)
    else:
        print(f"\n✅ Test passed: accuracy {result['accuracy']:.1%} meets threshold 75%")
        sys.exit(0)


if __name__ == "__main__":
    main()
