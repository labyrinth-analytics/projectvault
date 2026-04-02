"""Tests for CreditManager file isolation.

These tests address MEG-036: cross-file test pollution caused by
module-level DATA_DIR being cached at import time. Each test creates
its own CreditManager with a fresh temp directory.

MEG QA -- 2026-04-02
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

# Each test patches DATA_DIR/CREDITS_FILE directly to avoid import caching issues


class TestCreditManagerCorruptionRecovery(unittest.TestCase):
    """Verify CreditManager handles corrupted files correctly.

    Uses direct patching of module-level constants to avoid the
    cross-file test pollution bug (MEG-036).
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.credits_file = Path(self.tmpdir) / "credits.json"
        # Write clean initial state
        self.credits_file.write_text(json.dumps({"keys": {}}, indent=2))

    def _make_manager(self):
        """Create a CreditManager with patched paths."""
        import sys
        api_dir = os.path.join(os.path.dirname(__file__), "..")
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        import credits as credits_mod
        # Patch module-level constants
        old_data_dir = credits_mod.DATA_DIR
        old_credits_file = credits_mod.CREDITS_FILE
        credits_mod.DATA_DIR = Path(self.tmpdir)
        credits_mod.CREDITS_FILE = self.credits_file
        try:
            cm = credits_mod.CreditManager()
        finally:
            # We intentionally leave patched for the test duration
            pass
        return cm, credits_mod, old_data_dir, old_credits_file

    def tearDown(self):
        # Restore module-level constants if they were patched
        if hasattr(self, "_credits_mod"):
            self._credits_mod.DATA_DIR = self._old_data_dir
            self._credits_mod.CREDITS_FILE = self._old_credits_file

    def test_corrupted_json_raises_on_load(self):
        """Corrupted credits.json should raise JSONDecodeError on _load()."""
        self.credits_file.write_text("NOT JSON AT ALL {{{")
        cm, mod, old_dd, old_cf = self._make_manager()
        self._credits_mod = mod
        self._old_data_dir = old_dd
        self._old_credits_file = old_cf
        with self.assertRaises(json.JSONDecodeError):
            cm._load()

    def test_missing_keys_field_returns_no_keys(self):
        """credits.json with no 'keys' field should not have keys in data."""
        self.credits_file.write_text(json.dumps({"version": 1}))
        cm, mod, old_dd, old_cf = self._make_manager()
        self._credits_mod = mod
        self._old_data_dir = old_dd
        self._old_credits_file = old_cf
        data = cm._load()
        self.assertNotIn("keys", data)

    def test_empty_file_raises_on_load(self):
        """Empty credits.json should raise JSONDecodeError."""
        self.credits_file.write_text("")
        cm, mod, old_dd, old_cf = self._make_manager()
        self._credits_mod = mod
        self._old_data_dir = old_dd
        self._old_credits_file = old_cf
        with self.assertRaises(json.JSONDecodeError):
            cm._load()

    def test_generate_key_creates_valid_entry(self):
        """Fresh CreditManager can generate and validate keys."""
        cm, mod, old_dd, old_cf = self._make_manager()
        self._credits_mod = mod
        self._old_data_dir = old_dd
        self._old_credits_file = old_cf
        key = cm.generate_key(plan="starter", credits=10)
        self.assertTrue(cm.is_valid_key(key))
        self.assertEqual(cm.get_credits(key), 10)
        self.assertEqual(cm.get_plan(key), "starter")


class TestGitignoreRevenueProjection(unittest.TestCase):
    """Verify .gitignore blocks revenue projection files (added 2026-04-02)."""

    def test_root_gitignore_blocks_revenue_projections(self):
        """Root .gitignore should block *Revenue_Projection* patterns."""
        gitignore_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", ".gitignore"
        )
        if not os.path.exists(gitignore_path):
            self.skipTest("Root .gitignore not found")
        with open(gitignore_path) as f:
            content = f.read()
        self.assertIn("Revenue_Projection", content)
        self.assertIn("revenue_projection", content)
        self.assertIn("build_revenue_projection.py", content)


if __name__ == "__main__":
    unittest.main()
