# ==============================================================================
# state.py — LangGraph Agent State Definition
#
# WHAT IS LANGGRAPH STATE?
# LangGraph works like a flow chart. Each "node" in the chart is a Python
# function. The "state" is a typed dictionary that flows between nodes —
# each node reads what it needs and writes what it produces.
#
# Think of it like a baton in a relay race: each runner (node) adds info
# to it before passing it to the next runner.
# ==============================================================================
from typing import Optional
from typing_extensions import TypedDict


class FailureInfo(TypedDict):
    """Parsed output from the pytest failure log."""
    test_file_path: str           # e.g. "tests/test_orders.py"
    test_function_name: str       # e.g. "test_create_order"
    line_number: int              # Line where assertion failed
    assertion_error: str          # The raw assertion error message
    source_file_path: str         # The application file under test


class AgentState(TypedDict):
    """
    The complete state object passed through every node in the LangGraph.
    Optional fields start as None and are populated as the graph progresses.
    """
    # --- Populated by webhook handler (before graph starts) ---
    run_id: str                           # UUID of the pipeline_run record
    repo_full_name: str                   # e.g. "drizzle-org/my-service"
    pr_number: int
    commit_sha: str
    raw_ci_log: str                       # Full pytest output from CI
    mode: str                             # "MANUAL" or "AUTOPILOT"

    # --- Populated by Classifier Node ---
    failure_info: Optional[FailureInfo]
    failure_category: Optional[str]       # TEST_MISMATCH | APP_BUG | ENV_CONFIG | ...
    classification_reason: Optional[str]  # Plain-English explanation
    stop_reason: Optional[str]            # Set by stopper_node

    # --- Populated by file fetcher ---
    test_file_content: Optional[str]      # Raw content of the test file
    source_file_content: Optional[str]    # Raw content of the source file

    # --- Populated by HITL Gate ---
    user_hint: Optional[str]              # Developer's optional context hint

    # --- Populated by Fixer Node ---
    patched_test_file: Optional[str]      # The modified test file content
    patch_diff: Optional[str]             # Unified diff for the dashboard viewer

    # --- Populated by Validator ---
    validation_passed: Optional[bool]
    validation_error: Optional[str]       # New error if validation failed
    pr_url: Optional[str]                 # Link to the PR
    retry_count: int                      # Max 2 total attempts
