"""
fetcher.py — LangGraph File Fetcher Node

WHAT THIS DOES:
Before the classifier can make a good decision, it needs to SEE the code —
not just the error message. This node fetches:
  1. The failing test file (e.g. tests/test_orders.py)
  2. The source file it's testing (e.g. app/orders.py)

from GitHub using the App installation token we set up in Milestone 2.

WHY FETCH BEFORE CLASSIFYING?
With only the error message, Gemini might be 70% confident.
With the full file content, it's typically 95%+ confident.
Better context = better classification = fewer wrong decisions.

GRACEFUL DEGRADATION:
If a file can't be fetched (wrong path guess, private subdirectory, etc.)
we don't crash — we proceed with None and the classifier does its best
with whatever context is available.
"""
from langchain_core.runnables import RunnableConfig
from agent.state import AgentState


def _fetch_with_fallback(repo: str, path: str, ref: str, fetch_file_content) -> str | None:
    """
    Tries to fetch a file at a specific commit SHA first.
    Falls back to 'main' branch if the commit isn't found.
    This handles our dev test webhook (fake SHAs) gracefully.
    """
    for r in [ref, "main", "master"]:
        try:
            content = fetch_file_content(repo, path, r)
            if content:
                return content
        except Exception:
            continue
    return None


def fetcher_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    LangGraph node: fetches test + source file content from GitHub.
    Uses the failure_info parsed by the webhook handler to know which
    files to fetch. Falls back to main branch if exact commit not found.
    Tries multiple candidate source paths (app/, src/, lib/) in order.
    """
    fi     = state.get("failure_info") or {}
    repo   = state["repo_full_name"]
    ref    = state["commit_sha"]

    fetch_file_content = config["configurable"]["fetch_file_content"]
    _guess_source_file_candidates = config["configurable"]["_guess_source_file_candidates"]

    test_content   = None
    source_content = None

    test_path = fi.get("test_file_path")
    if test_path:
        test_content = _fetch_with_fallback(repo, test_path, ref, fetch_file_content)
        if not test_content:
            print(f"[fetcher] Could not fetch test file '{test_path}'")

    source_path = fi.get("source_file_path")
    if source_path:
        # Try the stored path first, then all heuristic candidates
        candidates = [source_path] + _guess_source_file_candidates(test_path or "")
        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            source_content = _fetch_with_fallback(repo, candidate, ref, fetch_file_content)
            if source_content:
                print(f"[fetcher] Found source file at '{candidate}'")
                # Update failure_info with the resolved path
                fi = {**fi, "source_file_path": candidate}
                break
        if not source_content:
            print(f"[fetcher] Could not fetch source file (tried: {list(seen)})")

    return {
        "test_file_content":   test_content,
        "source_file_content": source_content,
        "failure_info":        fi,
    }
