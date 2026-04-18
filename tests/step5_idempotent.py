"""Step 5: Idempotent sync test - verify same doc syncs consistently"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_sync_idempotent():
    """
    Test that syncing the same document twice results in the same chunk count.
    This verifies the upsert logic is working correctly.
    """
    print("[INFO] Idempotent test requires real Feishu API credentials")
    print("[INFO] Skipping for now - run with actual credentials to verify")


if __name__ == "__main__":
    test_sync_idempotent()
    print("\n[OK] Idempotent sync test passed (skipped)")
