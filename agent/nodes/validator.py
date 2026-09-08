"""
validator.py — LangGraph Validator Node

WHAT THIS NODE DOES:
After the fixer generates a patched test file, we validate the fix by running
pytest against the patched file in a temporary workspace directory.

THE PROCESS:
  1. Write the patched test file into the extracted workspace
  2. Run pytest with a 60-second timeout
  3. Parse the exit code — 0 = pass, anything else = fail
  4. Always clean up the temporary directory in finally
"""
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional

from langchain_core.runnables import RunnableConfig
from agent.state import AgentState

TIMEOUT_SECONDS = 60


def _fetch_optional_file(repo: str, path: str, ref: str, fetch_file_content) -> Optional[str]:
    """Fetch a file from GitHub, return None if not found."""
    for r in [ref, "main", "master"]:
        try:
            content = fetch_file_content(repo, path, r)
            if content:
                return content
        except Exception:
            continue
    return None


def validator_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    LangGraph node: runs the patched test in a Docker container.
    Returns validation_passed: True/False and validation_error with pytest output.
    """
    patched = state.get("patched_test_file")
    if not patched:
        return {
            "validation_passed": False,
            "validation_error": "No patched file to validate.",
        }

    fi        = state.get("failure_info") or {}
    test_path = fi.get("test_file_path", "tests/test.py")
    repo      = state.get("repo_full_name", "")
    ref       = state.get("commit_sha", "main")

    tmpdir = tempfile.mkdtemp(prefix="realive_validate_")
    print(f"[validator] Preparing workspace at {tmpdir}")

    fetch_file_content = config["configurable"]["fetch_file_content"]

    try:
        get_github_client = config["configurable"].get("get_github_client")
        if get_github_client:
            try:
                print(f"[validator] Downloading repository context...")
                gh = get_github_client(repo)
                repo_obj = gh.get_repo(repo)
                zip_url = repo_obj.get_archive_link("zipball", ref=ref)
                
                import urllib.request
                import zipfile
                import io
                from app.github.auth import get_installation_token
                
                token = get_installation_token(repo)
                req = urllib.request.Request(zip_url, headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                })
                with urllib.request.urlopen(req) as response:
                    with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                        z.extractall(tmpdir)
                
                top_dirs = os.listdir(tmpdir)
                if len(top_dirs) == 1 and os.path.isdir(os.path.join(tmpdir, top_dirs[0])):
                    workspace_dir = os.path.join(tmpdir, top_dirs[0])
                else:
                    workspace_dir = tmpdir
                print(f"[validator] Extracted repo to {workspace_dir}")
            except Exception as e:
                error_msg = f"Failed to fetch repository zipball from GitHub: {type(e).__name__}: {str(e)}"
                print(f"[validator] {error_msg}")
                return {
                    "validation_passed": False,
                    "validation_error": error_msg,
                }
        else:
            workspace_dir = tmpdir

        # ── Step 1: Write the patched test file ──────────────────────────────
        full_test_path = os.path.join(workspace_dir, test_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(full_test_path), exist_ok=True)
        with open(full_test_path, "w", encoding="utf-8") as f:
            f.write(patched)
        print(f"[validator] Wrote patch to {test_path}")

        # ── Step 2: Fetch requirements.txt via GitHub API ────────────────────
        req_content = _fetch_optional_file(repo, "requirements.txt", ref, fetch_file_content)
        if req_content:
            req_path = os.path.join(workspace_dir, "requirements.txt")
            with open(req_path, "w", encoding="utf-8") as f:
                f.write(req_content)

        # ── Step 3: Run pytest in clean environment ─────────────────────────
        # Strip backend secrets from the test process environment
        safe_env = {
            k: v for k, v in os.environ.items()
            if not any(sub in k.upper() for sub in ("KEY", "SECRET", "TOKEN", "DATABASE", "PASSWORD", "PRIVATE", "SUPABASE", "GROQ"))
        }
        safe_env["PYTHONPATH"] = workspace_dir

        test_cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header", "-q"]

        # If repo has requirements.txt, isolate dependencies into an ephemeral venv in tmpdir
        if req_content:
            try:
                venv_dir = os.path.join(tmpdir, ".venv")
                subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True, capture_output=True, timeout=30)
                python_bin = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")
                req_path = os.path.join(workspace_dir, "requirements.txt")
                subprocess.run([python_bin, "-m", "pip", "install", "-r", req_path, "pytest", "-q"], cwd=workspace_dir, check=False, timeout=60, capture_output=True)
                test_cmd = [python_bin, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header", "-q"]
            except Exception as venv_err:
                print(f"[validator] Ephemeral venv setup skipped ({venv_err}), using primary pytest runner")

        print(f"[validator] Running pytest on {test_path}")
        try:
            result = subprocess.run(
                test_cmd,
                cwd=workspace_dir,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
            output = (result.stdout + "\n" + result.stderr).strip()[-2000:]
            
            if result.returncode == 0:
                print(f"[validator] Tests PASSED")
                print(output[-300:])
                return {
                    "validation_passed": True,
                    "validation_error": None,
                }
            else:
                print(f"[validator] Tests FAILED")
                print(output[-300:])
                return {
                    "validation_passed": False,
                    "validation_error": output,
                }
        except subprocess.TimeoutExpired:
            return {
                "validation_passed": False,
                "validation_error": f"Validation timed out after {TIMEOUT_SECONDS}s.",
            }

    except Exception as exc:
        error = str(exc)
        if "timeout" in error.lower() or "timed out" in error.lower():
            return {
                "validation_passed": False,
                "validation_error": f"Validation timed out after {TIMEOUT_SECONDS}s.",
            }
        return {
            "validation_passed": False,
            "validation_error": f"Validator error: {error[:300]}",
        }

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"[validator] Cleaned up {tmpdir}")
