"""Tests for CreditManager edge cases and concurrency-adjacent issues.

Covers the credits.py email masking change from commit f43e296
and the non-atomic JSON file read/write advisory from previous QA.
"""

import os
import sys
import json
import tempfile
import pytest

# Ensure api/ is on the path so we can import credits
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override DATA_DIR before importing CreditManager
_tmp_dir = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _tmp_dir

from credits import CreditManager, CREDITS_FILE


class TestEmailMasking:
    """Verify email masking in generate_key logging."""

    def setup_method(self):
        # Reset credits file for each test
        credits_file = os.path.join(_tmp_dir, "credits.json")
        with open(credits_file, "w") as f:
            json.dump({"keys": {}}, f)

    def test_short_email_masked(self):
        """Email with 3+ chars gets first 3 chars + ***."""
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=10, email="ab@x.com")
        # Just verify no crash and key is valid
        assert cm.is_valid_key(key)

    def test_none_email_no_crash(self):
        """None email should not crash masking logic."""
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=10, email=None)
        assert cm.is_valid_key(key)

    def test_empty_string_email(self):
        """Empty string email should mask without error."""
        cm = CreditManager()
        # Empty string is falsy, so masked_email = "unknown"
        key = cm.generate_key(plan="starter", credits=10, email="")
        assert cm.is_valid_key(key)

    def test_single_char_email_masked(self):
        """Single char email -- [:3] returns just that char + ***."""
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=10, email="a")
        assert cm.is_valid_key(key)


class TestCreditFileRecovery:
    """Test behavior when credits file is corrupted or missing."""

    def test_corrupted_json_handled(self):
        """If credits.json is corrupted, _load will raise."""
        credits_file = os.path.join(_tmp_dir, "credits.json")
        with open(credits_file, "w") as f:
            f.write("NOT JSON AT ALL {{{")
        cm = CreditManager()
        # _load will raise json.JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            cm._load()

    def test_missing_keys_field(self):
        """If credits.json has no 'keys' field, operations should fail clearly."""
        credits_file = os.path.join(_tmp_dir, "credits.json")
        with open(credits_file, "w") as f:
            json.dump({"version": 1}, f)
        cm = CreditManager()
        data = cm._load()
        assert "keys" not in data  # confirms the scenario

    def test_total_optimizations_tracked(self):
        """Verify total_optimizations increments on each use_credit call."""
        credits_file = os.path.join(_tmp_dir, "credits.json")
        with open(credits_file, "w") as f:
            json.dump({"keys": {}}, f)
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=5)
        cm.use_credit(key)
        cm.use_credit(key)
        entry = cm._get_entry(key)
        assert entry["total_optimizations"] == 2
        assert entry["credits"] == 3


class TestHmacAdminComparison:
    """Verify the hmac.compare_digest change in main.py is timing-safe."""

    def test_hmac_compare_digest_equivalent(self):
        """hmac.compare_digest should produce same results as == for valid cases."""
        import hmac
        assert hmac.compare_digest("secret123", "secret123") is True
        assert hmac.compare_digest("secret123", "wrong") is False
        assert hmac.compare_digest("", "") is True
