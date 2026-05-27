"""
push_test_fixtures.py — One-time script to push test scenario to GitHub

This pushes the files that simulate a real CI failure in realive-test-target:
  - app/orders.py          (the "application" — returns data with 'currency' field)
  - tests/test_orders.py   (the "outdated test" — doesn't know about 'currency')
  - .github/workflows/ci.yml  (runs pytest and POSTs to our webhook on failure)

Run from backend/ directory with the venv active:
    .venv\\Scripts\\python scripts/push_test_fixtures.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from github import GithubException
from app.github.auth import get_github_client

REPO = "imshreyaskn/realive-test-target"
BRANCH = "main"

# ── File contents to push ─────────────────────────────────────────────────────

APP_ORDERS = '''\
"""
orders.py — Simulated orders API

This represents the CURRENT STATE of the application.
A developer recently added a 'currency' field to the response.
The test (test_orders.py) is outdated and doesn\'t know about it yet.
"""

def create_order(item: str, quantity: int) -> dict:
    """Creates an order and returns the response payload."""
    return {
        "id": 1,
        "item": item,
        "quantity": quantity,
        "total": quantity * 9.99,
        "currency": "USD",   # <-- newly added field (test doesn\'t know about this)
    }
'''

TEST_ORDERS = '''\
"""
test_orders.py — Outdated test suite for orders API

This test was written BEFORE the \'currency\' field was added to create_order().
It now fails because the response has extra keys the test didn\'t expect.

This is the exact scenario Realive is designed to fix.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.orders import create_order


def test_create_order():
    """
    Verifies a basic order creation.
    BROKEN: asserts the response has ONLY \'id\' and \'total\'.
    But the API now also returns \'currency\', \'item\', \'quantity\'.
    """
    response = create_order(item="Widget", quantity=2)

    # This assertion fails because response.keys() now includes
    # \'item\', \'quantity\', \'currency\' in addition to \'id\' and \'total\'
    assert "id" in response
    assert "total" in response
    assert set(response.keys()) == {"id", "total"}  # <-- THIS FAILS
'''

CI_WORKFLOW = '''\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install pytest

      - name: Run tests and capture output
        id: pytest
        run: |
          pytest tests/ --tb=short 2>&1 | tee pytest_output.txt
          echo "exit_code=${PIPESTATUS[0]}" >> $GITHUB_OUTPUT

      - name: Notify Realive on failure
        if: failure()
        env:
          WEBHOOK_SECRET: ${{ secrets.REALIVE_WEBHOOK_SECRET }}
        run: |
          CI_LOG=$(cat pytest_output.txt)

          PAYLOAD=$(python3 -c "
          import json, sys
          payload = {
              \\"repository\\": \\"${{ github.repository }}\\",
              \\"pr_number\\": ${{ github.event.pull_request.number || 0 }},
              \\"commit_sha\\": \\"${{ github.sha }}\\",
              \\"ci_log\\": open(\\"pytest_output.txt\\").read()
          }
          print(json.dumps(payload))
          ")

          # Compute HMAC-SHA256 signature
          SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | cut -d\' \' -f2)

          curl -X POST https://smee.io/realive-webhook \\
            -H "Content-Type: application/json" \\
            -H "X-Hub-Signature-256: sha256=$SIG" \\
            -d "$PAYLOAD"
'''

APP_INIT = '# Orders application package\n'
TESTS_INIT = '# Tests package\n'


def push_file(repo, path: str, content: str, message: str):
    """Creates or updates a file in the GitHub repo via the API."""
    from github import GithubException
    try:
        # Try to get existing file (needed for the SHA to update it)
        existing = repo.get_contents(path, ref=BRANCH)
        repo.update_file(path, message, content, existing.sha, branch=BRANCH)
        print(f"  [UPDATED] {path}")
    except GithubException:
        # File doesn't exist yet -- create it
        repo.create_file(path, message, content, branch=BRANCH)
        print(f"  [CREATED] {path}")


def main():
    print(f"\nPushing test fixtures to {REPO}...\n")

    gh = get_github_client(REPO)
    repo = gh.get_repo(REPO)

    files = [
        ("app/__init__.py",              APP_INIT,      "chore: add app package"),
        ("app/orders.py",                APP_ORDERS,    "feat: add currency field to create_order"),
        ("tests/__init__.py",            TESTS_INIT,    "chore: add tests package"),
        ("tests/test_orders.py",         TEST_ORDERS,   "test: add order tests (outdated — Realive demo)"),
        (".github/workflows/ci.yml",     CI_WORKFLOW,   "ci: add pytest workflow with Realive webhook"),
    ]

    for path, content, message in files:
        push_file(repo, path, content, message)

    print(f"\nDone! Check {REPO} on GitHub.")
    print("The CI workflow will run automatically and fail -- that's expected.")
    print("It will POST the failure to smee.io/realive-webhook when it does.\n")


if __name__ == "__main__":
    main()
