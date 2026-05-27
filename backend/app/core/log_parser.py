"""
log_parser.py — Pytest failure log parser

WHAT THIS DOES:
When GitHub Actions runs pytest and it fails, the raw output looks like this:

    FAILED tests/test_orders.py::test_create_order - AssertionError: assert ...
    
    ================================ FAILURES ==================================
    _________________________ test_create_order _______________________________
    
    tests/test_orders.py:15: AssertionError
    E   AssertionError: assert set(response.keys()) == {'id', 'total'}
    E   Extra items in the left set:
    E   'currency'

This parser reads that messy text and pulls out the structured information
we need: which file, which function, which line, what error.

WHY REGEX?
The pytest `--tb=short` format is consistent and well-documented. Regex
(regular expressions) is the right tool for parsing structured text patterns.
Each pattern targets a specific line format in the output.
"""
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedFailure:
    """
    Structured output from parsing a pytest failure log.
    One of these per failed test function.
    """
    test_file_path: str        # e.g. "tests/test_orders.py"
    test_function_name: str    # e.g. "test_create_order"
    line_number: int           # Line in the test file where assertion failed
    assertion_error: str       # The full assertion error message
    source_file_path: str      # Best-guess at the source file being tested


# ── Regex Patterns ────────────────────────────────────────────────────────────
# These match the specific line formats that pytest --tb=short produces.

# Matches: "FAILED tests/test_orders.py::test_create_order - AssertionError: ..."
# Groups:  (file_path, function_name, error_summary)
FAILED_LINE_RE = re.compile(
    r"FAILED\s+([\w/\\.\-]+\.py)::(\w+)\s*-\s*(.+)"
)

# Matches: "tests/test_orders.py:15: AssertionError"
# Groups:  (file_path, line_number)
ERROR_LOCATION_RE = re.compile(
    r"([\w/\\.\-]+\.py):(\d+):\s+\w+Error"
)

# Matches lines starting with "E " — these are the actual error message lines
# Example: "E   AssertionError: assert {'id': 1} == {'id': 1, 'total': 100}"
ERROR_MESSAGE_RE = re.compile(r"^E\s{3}(.+)", re.MULTILINE)

# Guess at source file from test file path
# "tests/test_orders.py" → "app/orders.py" (common pytest convention)
def _guess_source_file(test_file_path: str) -> str:
    """
    Infers the application source file from the test file path.

    Convention: tests/test_X.py → app/X.py (or src/X.py)
    Returns the most likely candidate. The fetcher tries fallback paths
    (main, master) so a wrong guess fails gracefully.
    """
    filename = test_file_path.split("/")[-1]   # "test_orders.py"
    source_name = filename.replace("test_", "") # "orders.py"

    # Return candidates in priority order; first one is the best guess.
    # The fetcher will fall back to "main"/"master" if the file isn't found.
    candidates = [f"{prefix}/{source_name}" for prefix in ("app", "src", "lib")]
    return candidates[0]  # "app/orders.py"


def _guess_source_file_candidates(test_file_path: str) -> list[str]:
    """Returns all candidate source paths for the fetcher to try in order."""
    filename = test_file_path.split("/")[-1]
    source_name = filename.replace("test_", "")
    return [f"{prefix}/{source_name}" for prefix in ("app", "src", "lib")]


def parse_pytest_output(ci_log: str) -> list[ParsedFailure]:
    """
    Parses raw pytest --tb=short output and returns a list of ParsedFailure objects.
    
    Returns an empty list if:
    - No FAILED lines are found
    - The output format doesn't match what we expect
    
    Args:
        ci_log: Raw string output from pytest --tb=short

    Returns:
        List of ParsedFailure dataclasses.
    """
    failures = []
    
    # We iterate over all matches of FAILED lines
    # To correctly extract the error message for each failure, we split the log by the FAILED lines
    # or just find all FAILED matches and then extract the text between them.
    
    matches = list(FAILED_LINE_RE.finditer(ci_log))
    if not matches:
        return failures

    for i, failed_match in enumerate(matches):
        test_file_path = failed_match.group(1).replace("\\", "/")
        test_function_name = failed_match.group(2)
        
        # The block of text for this failure is from the current match end
        # up to the start of the next match (or end of string)
        start_idx = failed_match.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(ci_log)
        block = ci_log[start_idx:end_idx]

        # Find the error location (file:line_number) in this block
        line_number = 0
        location_match = ERROR_LOCATION_RE.search(block)
        if location_match:
            line_number = int(location_match.group(2))

        # Collect all "E  " lines — these form the assertion error message
        error_lines = ERROR_MESSAGE_RE.findall(block)
        assertion_error = "\n".join(error_lines).strip() if error_lines else failed_match.group(3)

        source_file_path = _guess_source_file(test_file_path)

        failures.append(ParsedFailure(
            test_file_path=test_file_path,
            test_function_name=test_function_name,
            line_number=line_number,
            assertion_error=assertion_error,
            source_file_path=source_file_path,
        ))

    return failures
