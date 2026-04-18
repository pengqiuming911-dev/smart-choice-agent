"""Step 6 Audit Integrity Test - Test that all required fields are logged correctly"""
import json
import sys
import os
import uuid
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_service.agent.workflow import run_chat
from rag_service.agent.compliance import add_to_whitelist
from rag_service.models.db import get_session_history


def test_audit_log_integrity() -> Dict[str, Any]:
    """
    Test that audit logs contain all required fields.

    Returns:
        Dict with test results
    """
    add_to_whitelist("ou_test_qualified")

    # Generate unique session ID for this test
    test_session_id = str(uuid.uuid4())
    test_question = "私募基金的投资策略有哪些？"

    print("=" * 70)
    print("Step 6 Audit Integrity Test")
    print("=" * 70)

    print(f"\nTest Session ID: {test_session_id}")
    print(f"Test Question: {test_question}")

    # Run chat
    result = run_chat(
        question=test_question,
        user_open_id="ou_test_qualified",
        user_name="AuditTestUser",
        session_id=test_session_id,
    )

    print(f"Result blocked: {result.get('blocked')}")
    print(f"Answer length: {len(result.get('answer', ''))}")

    # Query audit log
    try:
        logs = get_session_history(test_session_id)

        if not logs:
            print("\n✗ FAIL: No audit log found for session")
            return {
                "passed": False,
                "error": "No audit log found",
            }

        log = logs[0]  # Get first (and should be only) log entry

        # Check required fields
        required_fields = {
            "session_id": test_session_id,
            "user_open_id": "ou_test_qualified",
            "user_name": "AuditTestUser",
            "question": test_question,
            "answer": result.get("answer"),
            "latency_ms": result.get("latency_ms"),
            "llm_model": "MiniMax-M2.7",
        }

        results = []
        all_passed = True

        print("\nField Checks:")
        for field_name, expected in required_fields.items():
            actual = log.get(field_name)
            if field_name == "answer":
                # Answer might be truncated or have slight differences
                passed = actual is not None and len(actual) > 0
            elif field_name == "latency_ms":
                passed = actual is not None and actual > 0
            else:
                passed = actual == expected

            status = "✓" if passed else "✗"
            if not passed:
                all_passed = False
                print(f"  {status} {field_name}: expected '{expected}', got '{actual}'")
            else:
                print(f"  {status} {field_name}: {actual}")

        # Check citations format
        citations = result.get("citations", [])
        citations_valid = isinstance(citations, list)

        print(f"\n  {'✓' if citations_valid else '✗'} citations format: {type(citations)}")
        if citations_valid and len(citations) > 0:
            print(f"    First citation: {citations[0]}")

        # Check retrieved_chunks
        chunks = result.get("chunks", [])
        chunks_valid = isinstance(chunks, list)

        print(f"\n  {'✓' if chunks_valid else '✗'} chunks format: {type(chunks)}")

        print("\n" + "=" * 70)
        if all_passed and citations_valid and chunks_valid:
            print("Audit Integrity Test: PASSED")
        else:
            print("Audit Integrity Test: FAILED")
        print("=" * 70)

        return {
            "passed": all_passed and citations_valid and chunks_valid,
            "session_id": test_session_id,
            "log_found": True,
            "all_fields_passed": all_passed,
            "citations_valid": citations_valid,
            "chunks_valid": chunks_valid,
        }

    except Exception as e:
        print(f"\n✗ FAIL: Error querying audit log: {e}")
        import traceback
        traceback.print_exc()

        return {
            "passed": False,
            "error": str(e),
        }


def test_audit_log_latency() -> Dict[str, Any]:
    """
    Test that latency is reasonable (< 10 seconds).
    """
    add_to_whitelist("ou_test_qualified")

    test_session_id = str(uuid.uuid4())

    print("\n" + "=" * 70)
    print("Audit Log Latency Test")
    print("=" * 70)

    result = run_chat(
        question="什么是私募基金？",
        user_open_id="ou_test_qualified",
        user_name="LatencyTest",
        session_id=test_session_id,
    )

    latency_ms = result.get("latency_ms", 0)
    latency_sec = latency_ms / 1000

    passed = latency_ms < 10000  # < 10 seconds

    print(f"Latency: {latency_ms}ms ({latency_sec:.2f}s)")
    print(f"Threshold: < 10000ms (10s)")
    print(f"Result: {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        "passed": passed,
        "latency_ms": latency_ms,
        "threshold_ms": 10000,
    }


def test_multiple_sessions() -> Dict[str, Any]:
    """
    Test that multiple sessions are logged separately.
    """
    add_to_whitelist("ou_test_qualified")

    print("\n" + "=" * 70)
    print("Multiple Sessions Isolation Test")
    print("=" * 70)

    session_1 = str(uuid.uuid4())
    session_2 = str(uuid.uuid4())

    question_1 = "第一个问题：什么是PE？"
    question_2 = "第二个问题：什么是VC？"

    # Run two separate sessions
    result_1 = run_chat(
        question=question_1,
        user_open_id="ou_test_qualified",
        user_name="IsolationTest",
        session_id=session_1,
    )

    result_2 = run_chat(
        question=question_2,
        user_open_id="ou_test_qualified",
        user_name="IsolationTest",
        session_id=session_2,
    )

    # Query logs
    logs_1 = get_session_history(session_1)
    logs_2 = get_session_history(session_2)

    passed = (
        len(logs_1) == 1 and
        len(logs_2) == 1 and
        logs_1[0].get("question") == question_1 and
        logs_2[0].get("question") == question_2
    )

    if passed:
        print(f"✓ Session 1 logged correctly: {logs_1[0].get('question')}")
        print(f"✓ Session 2 logged correctly: {logs_2[0].get('question')}")
    else:
        print(f"✗ FAIL: Sessions not properly isolated")
        print(f"  Session 1 logs: {len(logs_1)}")
        print(f"  Session 2 logs: {len(logs_2)}")

    return {
        "passed": passed,
        "session_1_logs": len(logs_1),
        "session_2_logs": len(logs_2),
    }


def main():
    """Run all audit integrity tests"""
    results = []

    # Test 1: Basic audit log integrity
    results.append(("Audit Log Integrity", test_audit_log_integrity()))

    # Test 2: Latency
    results.append(("Latency", test_audit_log_latency()))

    # Test 3: Session isolation
    results.append(("Session Isolation", test_multiple_sessions()))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"  {status} {name}")
        if not result["passed"]:
            all_passed = False

    if not all_passed:
        print("\n❌ Some audit tests FAILED")
        sys.exit(1)
    else:
        print("\n✅ All audit tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
