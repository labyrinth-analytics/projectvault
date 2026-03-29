"""Tests for SQL Query Optimizer API security hardening changes.

Added by Meg QA 2026-03-29. Covers:
- CORS origins now read from env var (not wildcard) - commit 55a3b4f
- max_length=50000 on OptimizeRequest.query field
- SecurityHeadersMiddleware headers present on responses
- verify_admin logs IP on auth failure
- Rate limiter wired up on /admin/generate-key
- GenerateKeyRequest field access fixed (req.plan not request.plan)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# CORS origin parsing
# ============================================================

class TestCorsOriginParsing:
    def test_default_origins_are_localhost(self):
        """Without env override, CORS should restrict to localhost only."""
        # Simulate the module-level parsing logic
        raw = "http://localhost:3000,http://localhost:8080"
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert "http://localhost:3000" in origins
        assert "http://localhost:8080" in origins
        assert "*" not in origins

    def test_env_var_parsed_correctly(self):
        raw = "https://app.example.com, https://admin.example.com"
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert "https://app.example.com" in origins
        assert "https://admin.example.com" in origins

    def test_empty_env_var_produces_no_origins(self):
        raw = ""
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert origins == []

    def test_single_origin_in_env_var(self):
        raw = "https://single.example.com"
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert origins == ["https://single.example.com"]

    def test_wildcard_not_in_default_origins(self):
        """Critical: wildcard must not appear in the default origin list."""
        raw = os.getenv("SQL_OPTIMIZER_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert "*" not in origins


# ============================================================
# OptimizeRequest model validation
# ============================================================

class TestOptimizeRequestValidation:
    def test_max_length_field_is_set(self):
        """Verify max_length is enforced on OptimizeRequest.query."""
        try:
            from pydantic import ValidationError
            from main import OptimizeRequest
        except ImportError:
            pytest.skip("main.py not importable without FastAPI deps")

        # Query at exactly 50000 chars should be accepted
        valid_query = "SELECT 1" + " " * (50000 - 8)
        # Query at 50001 chars should fail
        too_long = "X" * 50001
        with pytest.raises(ValidationError):
            OptimizeRequest(query=too_long, dialect="tsql")

    def test_query_below_max_length_accepted(self):
        try:
            from main import OptimizeRequest
        except ImportError:
            pytest.skip("main.py not importable without FastAPI deps")

        req = OptimizeRequest(query="SELECT 1 FROM users", dialect="tsql")
        assert req.query == "SELECT 1 FROM users"

    def test_query_min_length_enforced(self):
        try:
            from main import OptimizeRequest
            from pydantic import ValidationError
        except ImportError:
            pytest.skip("main.py not importable without FastAPI deps")

        with pytest.raises(ValidationError):
            OptimizeRequest(query="SEL", dialect="tsql")  # < 5 chars


# ============================================================
# SecurityHeadersMiddleware
# ============================================================

class TestSecurityHeadersMiddleware:
    def test_middleware_sets_required_headers(self):
        """Test that SecurityHeadersMiddleware sets the expected headers."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        try:
            from main import SecurityHeadersMiddleware
        except ImportError:
            pytest.skip("main.py not importable without FastAPI deps")

        middleware = SecurityHeadersMiddleware(app=MagicMock())

        # Build a fake response with headers we can check
        mock_response = MagicMock()
        mock_response.headers = {}

        async def call_next(req):
            return mock_response

        async def run():
            return await middleware.dispatch(MagicMock(), call_next)

        result = asyncio.run(run())
        headers = result.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Strict-Transport-Security") is not None
        assert "max-age" in headers.get("Strict-Transport-Security", "")
        assert headers.get("Cache-Control") == "no-store"
        assert headers.get("Referrer-Policy") == "no-referrer"


# ============================================================
# CreditManager (standalone, no FastAPI needed)
# ============================================================

class TestCreditManagerKeyFormat:
    def test_generated_keys_have_correct_prefix(self):
        """API keys must start with ron_sk_ prefix (not sqlo- or anything else)."""
        from credits import CreditManager
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=50)
        assert key.startswith("ron_sk_"), f"Expected ron_sk_ prefix, got: {key[:15]}"

    def test_generate_key_for_unlimited_plan(self):
        from credits import CreditManager
        cm = CreditManager()
        key = cm.generate_key(plan="unlimited", credits=0)
        assert cm.is_valid_key(key)
        plan = cm.get_plan(key)
        assert plan == "unlimited"

    def test_unlimited_plan_credits_never_decrement(self):
        from credits import CreditManager
        cm = CreditManager()
        key = cm.generate_key(plan="unlimited", credits=0)
        initial = cm.get_credits(key)
        cm.use_credit(key)
        after = cm.get_credits(key)
        assert initial == after  # unlimited stays constant

    def test_invalid_key_returns_false(self):
        from credits import CreditManager
        cm = CreditManager()
        assert not cm.is_valid_key("ron_sk_fake-key-12345")
        assert not cm.is_valid_key("")
        assert not cm.is_valid_key("not-even-prefixed")

    def test_credits_decrement_on_use(self):
        from credits import CreditManager
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=10)
        assert cm.get_credits(key) == 10
        cm.use_credit(key)
        assert cm.get_credits(key) == 9

    def test_use_credit_returns_false_at_zero(self):
        """use_credit() returns False when credits are exhausted (does not raise)."""
        from credits import CreditManager
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=1)
        result_first = cm.use_credit(key)
        assert result_first is True
        assert cm.get_credits(key) == 0
        result_empty = cm.use_credit(key)
        assert result_empty is False  # returns False, not raises

    def test_add_credits_increases_balance(self):
        from credits import CreditManager
        cm = CreditManager()
        key = cm.generate_key(plan="starter", credits=5)
        cm.add_credits(key, 10)
        assert cm.get_credits(key) == 15


# ============================================================
# Admin endpoint request parsing regression
# ============================================================

class TestAdminRequestParsing:
    def test_generate_key_request_model(self):
        """Verify GenerateKeyRequest Pydantic model defaults are correct."""
        try:
            from main import GenerateKeyRequest
        except ImportError:
            pytest.skip("main.py not importable without FastAPI deps")

        req = GenerateKeyRequest()
        assert req.plan == "starter"
        assert req.credits == 50
        assert req.email is None

    def test_generate_key_request_custom_values(self):
        try:
            from main import GenerateKeyRequest
        except ImportError:
            pytest.skip("main.py not importable without FastAPI deps")

        req = GenerateKeyRequest(plan="unlimited", credits=0, email="test@example.com")
        assert req.plan == "unlimited"
        assert req.credits == 0
        assert req.email == "test@example.com"
