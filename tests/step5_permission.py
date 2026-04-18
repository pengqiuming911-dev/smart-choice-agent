"""Step 5: Permission sync test"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_permission_flow():
    """Test permission sync flow"""
    from rag_service.models.db import set_document_permissions, get_accessible_doc_ids

    # Test setting permissions
    test_doc_id = "test_doc_permission_001"

    permissions = [
        {"principal_type": "user", "principal_id": "ou_test_user_1", "perm": "read"},
        {"principal_type": "dept", "principal_id": "dept_investment", "perm": "read"},
        {"principal_type": "tenant", "principal_id": "all", "perm": "read"},
    ]

    count = set_document_permissions(test_doc_id, permissions)
    assert count == 3, f"Expected 3 permissions, got {count}"

    # Test querying accessible docs
    accessible = get_accessible_doc_ids("ou_test_user_1")
    assert test_doc_id in accessible, "User should have access to test doc"

    accessible = get_accessible_doc_ids("ou_other_user")
    # Should NOT have access (only ou_test_user_1 and dept)
    assert test_doc_id not in accessible, "Other user should not have access"

    print("[PASS] Permission flow works correctly")


if __name__ == "__main__":
    test_permission_flow()
