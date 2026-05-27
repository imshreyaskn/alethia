"""
test_log_parser.py — Unit tests for the pytest log parser

WHY UNIT TESTS?
Unit tests verify one small piece of code in isolation. For the log parser
this is critical — if the parser is broken, every downstream milestone
(classifier, fixer, validator) gets garbage input.

We test with REAL pytest --tb=short output strings, so the tests document
exactly what formats the parser handles.

Run with:
    cd backend
    .venv\\Scripts\\pytest tests/ -v
"""
import pytest
from app.core.log_parser import parse_pytest_output, ParsedFailure


# ── Fixture: realistic pytest --tb=short output ───────────────────────────────
# This is exactly what GitHub Actions captures when pytest fails

ASSERTION_ERROR_LOG = """
============================= test session starts ==============================
platform linux -- Python 3.12.0, pytest-8.3.3
collected 3 items

tests/test_orders.py::test_create_order FAILED                           [ 33%]
tests/test_orders.py::test_list_orders PASSED                            [ 66%]
tests/test_orders.py::test_get_order PASSED                              [100%]

=================================== FAILURES ===================================
__________________________ test_create_order ___________________________________

tests/test_orders.py:15: AssertionError
E   AssertionError: assert set(response.keys()) == {'id', 'total'}
E   Extra items in the left set:
E   'currency'

=========================== short test summary info ============================
FAILED tests/test_orders.py::test_create_order - AssertionError: assert set(response.keys()) == {'id', 'total'}
1 failed, 2 passed in 0.42s
"""

MISSING_FIELD_LOG = """
FAILED tests/test_users.py::test_user_profile - AssertionError: assert 'avatar_url' in response
tests/test_users.py:28: AssertionError
E   AssertionError: assert 'avatar_url' in response
E   where response = {'id': 42, 'email': 'test@example.com'}
"""

TYPE_ERROR_LOG = """
FAILED tests/test_payments.py::test_process_payment - TypeError: process_payment() got an unexpected keyword argument 'currency'
tests/test_payments.py:44: TypeError
E   TypeError: process_payment() got an unexpected keyword argument 'currency'
"""

NO_FAILURE_LOG = """
============================= test session starts ==============================
collected 2 items

tests/test_health.py::test_ping PASSED                                   [ 50%]
tests/test_health.py::test_version PASSED                                [100%]

============================== 2 passed in 0.05s ==============================
"""

EMPTY_LOG = ""


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestParseAssertionError:
    """The primary case: an outdated assertion in a test function."""

    def test_extracts_test_file_path(self):
        result = parse_pytest_output(ASSERTION_ERROR_LOG)
        assert result is not None
        assert result.test_file_path == "tests/test_orders.py"

    def test_extracts_function_name(self):
        result = parse_pytest_output(ASSERTION_ERROR_LOG)
        assert result.test_function_name == "test_create_order"

    def test_extracts_line_number(self):
        result = parse_pytest_output(ASSERTION_ERROR_LOG)
        assert result.line_number == 15

    def test_extracts_assertion_error(self):
        result = parse_pytest_output(ASSERTION_ERROR_LOG)
        assert "currency" in result.assertion_error
        assert "assert set(response.keys())" in result.assertion_error

    def test_guesses_source_file(self):
        result = parse_pytest_output(ASSERTION_ERROR_LOG)
        # "tests/test_orders.py" → "app/orders.py"
        assert result.source_file_path == "app/orders.py"


class TestParseMissingField:
    """A test that checks for a field that doesn't exist yet."""

    def test_extracts_function_name(self):
        result = parse_pytest_output(MISSING_FIELD_LOG)
        assert result.test_function_name == "test_user_profile"

    def test_extracts_file_path(self):
        result = parse_pytest_output(MISSING_FIELD_LOG)
        assert result.test_file_path == "tests/test_users.py"

    def test_error_contains_field_name(self):
        result = parse_pytest_output(MISSING_FIELD_LOG)
        assert "avatar_url" in result.assertion_error


class TestParseTypeError:
    """Non-assertion errors — useful for classifier to detect app bugs."""

    def test_extracts_function_name(self):
        result = parse_pytest_output(TYPE_ERROR_LOG)
        assert result.test_function_name == "test_process_payment"

    def test_extracts_error_message(self):
        result = parse_pytest_output(TYPE_ERROR_LOG)
        assert "unexpected keyword argument" in result.assertion_error


class TestNoFailure:
    """When all tests pass, parser should return None."""

    def test_returns_none_on_all_passed(self):
        result = parse_pytest_output(NO_FAILURE_LOG)
        assert result is None

    def test_returns_none_on_empty_log(self):
        result = parse_pytest_output(EMPTY_LOG)
        assert result is None


class TestReturnType:
    """Parser always returns ParsedFailure or None — never raises."""

    def test_returns_parsed_failure_instance(self):
        result = parse_pytest_output(ASSERTION_ERROR_LOG)
        assert isinstance(result, ParsedFailure)

    def test_never_raises_on_garbage_input(self):
        # Should silently return None, not crash
        result = parse_pytest_output("this is not pytest output at all!!!")
        assert result is None
