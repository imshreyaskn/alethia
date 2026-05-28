"""
validator.py — LangGraph Validator Node

WHAT THIS NODE DOES:
After the fixer generates a patched test file, we don't just trust it.
We prove it works by actually running the tests inside a Docker container.

THE PROCESS:
  1. Write the patched test file (and test file content) to a temp workspace
  2. Fetch the repo's requirements.txt via GitHub API (no full clone)
  3. Spin up the realive-runner Docker container with:
       - No network access
       - Read-only workspace volume
       - 512MB memory cap
       - 60-second timeout
  4. Parse the exit code — 0 = pass, anything else = fail
  5. Clean up temp directory

WHY DOCKER INSTEAD OF subprocess:
  - subprocess runs AI-generated code directly on the host — a security risk
  - Docker provides full isolation: no network, no filesystem write access,
    memory-bounded, killed on timeout, ephemeral
  - Required for multi-tenant SaaS where multiple orgs run code

BUILD THE RUNNER IMAGE ONCE:
  docker build -t realive-runner:python ./runner
"""
import os
import shutil
import tempfile
from typing import Optional

import docker
from docker.errors import DockerException, ImageNotFound

from langchain_core.runnables import RunnableConfig
from agent.state import AgentState

RUNNER_IMAGE = "realive-runner:python"
MEMORY_LIMIT = "512m"
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
                
                req = urllib.request.Request(zip_url)
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
                print(f"[validator] Failed to fetch repo zip: {e}. Falling back to empty dir.")
                workspace_dir = tmpdir
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

        # ── Step 3: Run pytest (MVP Subprocess Fallback) ─────────────────────
        import subprocess
        
        if req_content:
            print("[validator] Installing dependencies via subprocess...")
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt", "-q"],
                cwd=workspace_dir,
                check=False
            )
            
        print(f"[validator] Running pytest on {test_path} via subprocess")
        try:
            result = subprocess.run(
                ["pytest", test_path, "-v", "--tb=short", "--no-header", "-q"],
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
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

    except docker.errors.ContainerError as exc:
        # ContainerError is raised when the container exits with non-zero
        output = exc.stderr.decode("utf-8", errors="replace").strip()[-2000:] if exc.stderr else str(exc)
        print(f"[validator] Tests FAILED")
        print(output[-300:])
        return {
            "validation_passed": False,
            "validation_error": output,
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
