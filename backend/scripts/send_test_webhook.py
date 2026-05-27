"""
send_test_webhook.py — Manually fires a test webhook payload at the local backend.
Run from backend/ with the venv active:
    .venv\Scripts\python scripts/send_test_webhook.py
"""
import hmac
import hashlib
import json
import urllib.request

CI_LOG = (
    "============================= test session starts ==============================\n"
    "platform linux -- Python 3.12.0, pytest-8.3.3\n"
    "collected 1 item\n\n"
    "tests/test_orders.py::test_create_order FAILED                           [100%]\n\n"
    "=================================== FAILURES ===================================\n"
    "__________________________ test_create_order ___________________________________\n\n"
    "tests/test_orders.py:22: AssertionError\n"
    'E   AssertionError: assert set(response.keys()) == {"id", "total"}\n'
    "E   Extra items in the left set:\n"
    'E   "currency"\n'
    'E   "item"\n'
    'E   "quantity"\n\n'
    "=========================== short test summary info ============================\n"
    'FAILED tests/test_orders.py::test_create_order - AssertionError: assert set(response.keys()) == {"id", "total"}\n'
    "1 failed in 0.42s\n"
)

payload = {
    "repository": "imshreyaskn/realive-test-target",
    "pr_number": 0,
    "commit_sha": "abc1234def5678",
    "ci_log": CI_LOG,
}

body = json.dumps(payload).encode()
secret = b"realive_secret_123"
sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "http://localhost:8000/api/webhook/github",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": sig,
    },
)

print("Sending test webhook to http://localhost:8000/api/webhook/github ...")
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode())
    print("\nResponse:")
    print(json.dumps(result, indent=2))
