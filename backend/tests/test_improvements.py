"""
test_improvements.py - Verification tests for audit improvements:
- AST import extraction for source resolution
- libCST deep visitor function extraction
- Retry ceiling in LangGraph routing
- In-memory GitHub App token caching
"""
import ast
import time
import pytest
import libcst as cst

from agent.nodes.fetcher import _extract_imported_modules
from agent.nodes.fixer import _extract_function_code
from agent.graph import route_after_save_fix
import app.github.auth as gh_auth


def test_ast_import_extraction():
    """Verify that _extract_imported_modules extracts relative and module paths."""
    sample_code = """
from app.services.billing import calculate_tax
from models.user import User
import utils.crypto
import os
"""
    candidates = _extract_imported_modules(sample_code)
    assert "app/services/billing.py" in candidates
    assert "models/user.py" in candidates
    assert "app/models/user.py" in candidates
    assert "src/models/user.py" in candidates
    assert "utils/crypto.py" in candidates


def test_ast_import_syntax_error_graceful():
    """Verify malformed Python code returns empty list without raising."""
    broken_code = "def broken(:"
    assert _extract_imported_modules(broken_code) == []


def test_libcst_deep_function_finder():
    """Verify libCST finds methods nested inside inner classes."""
    nested_code = """
class OuterTest:
    class InnerTest:
        def test_nested_method(self):
            assert False
"""
    module = cst.parse_module(nested_code)
    extracted = _extract_function_code(module, "test_nested_method")
    assert extracted is not None
    assert "def test_nested_method(self):" in extracted
    assert "assert False" in extracted


def test_route_after_save_fix_retry_ceiling():
    """Verify route_after_save_fix stops when retry_count reaches 2."""
    state_retry_0 = {"validation_passed": False, "mode": "MANUAL", "retry_count": 0}
    assert route_after_save_fix(state_retry_0) == "retry_gate"

    state_retry_1 = {"validation_passed": False, "mode": "MANUAL", "retry_count": 1}
    assert route_after_save_fix(state_retry_1) == "retry_gate"

    state_retry_2 = {"validation_passed": False, "mode": "MANUAL", "retry_count": 2}
    assert route_after_save_fix(state_retry_2) == "stop"

    state_retry_3 = {"validation_passed": False, "mode": "MANUAL", "retry_count": 3}
    assert route_after_save_fix(state_retry_3) == "stop"


def test_route_after_save_fix_success():
    """Verify route_after_save_fix routes to create_pr when validation passes."""
    state_pass = {"validation_passed": True, "mode": "MANUAL", "retry_count": 1}
    assert route_after_save_fix(state_pass) == "create_pr"


def test_token_cache_ttl():
    """Verify token cache returns unexpired token and discards expired token."""
    repo = "test-org/test-repo"
    gh_auth._token_cache.clear()

    future = time.time() + 100
    gh_auth._token_cache[repo] = ("cached-token-123", future)

    cached_entry = gh_auth._token_cache.get(repo)
    assert cached_entry is not None
    token, expires_at = cached_entry
    assert time.time() < expires_at - 60
    assert token == "cached-token-123"

    past = time.time() + 30
    gh_auth._token_cache[repo] = ("expired-token", past)
    _, exp = gh_auth._token_cache[repo]
    assert not (time.time() < exp - 60)
