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
        # ── Step 1: Write the patched test file ──────────────────────────────
        full_test_path = os.path.join(tmpdir, test_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(full_test_path), exist_ok=True)
        with open(full_test_path, "w", encoding="utf-8") as f:
            f.write(patched)
        print(f"[validator] Wrote patch to {test_path}")

        # ── Step 2: Fetch requirements.txt via GitHub API (no clone) ─────────
        req_content = _fetch_optional_file(repo, "requirements.txt", ref, fetch_file_content)
        if req_content:
            req_path = os.path.join(tmpdir, "requirements.txt")
            with open(req_path, "w", encoding="utf-8") as f:
                f.write(req_content)
            print("[validator] Fetched requirements.txt")

        # ── Step 3: Run pytest (MVP Subprocess Fallback) ─────────────────────
        
        # [NOTE FOR FREE DEPLOYMENT]
        # The following Docker implementation has been commented out because free hosting 
        # platforms like Render do not support Docker-in-Docker. Instead, we use `subprocess` 
        # to run the tests directly on the host for this MVP. This is less secure but works 
        # for a trusted, single-tenant deployment.
        
        """
        # --- ORIGINAL DOCKER IMPLEMENTATION ---
        try:
            client = docker.from_env()
        except DockerException as e:
            return {
                "validation_passed": False,
                "validation_error": (
                    f"Docker not available: {e}. "
                    "Ensure Docker is running and the socket is mounted."
                ),
            }

        # Verify image exists
        try:
            client.images.get(RUNNER_IMAGE)
        except ImageNotFound:
            return {
                "validation_passed": False,
                "validation_error": (
                    f"Runner image '{RUNNER_IMAGE}' not found. "
                    "Build it with: docker build -t realive-runner:python ./runner"
                ),
            }

        # Install dependencies first if requirements.txt is present.
        if req_content:
            print("[validator] Installing dependencies...")
            prep = client.containers.run(
                image=RUNNER_IMAGE,
                command="pip install -r /workspace/requirements.txt -q",
                volumes={tmpdir: {"bind": "/workspace", "mode": "rw"}},
                mem_limit=MEMORY_LIMIT,
                network_mode="none",
                remove=True,
                stdout=True,
                stderr=True,
            )

        # Run the actual test
        print(f"[{test_path}] Running pytest on {test_path} in Docker")
        result = client.containers.run(
            image=RUNNER_IMAGE,
            command=f"pytest {test_path} -v --tb=short --no-header -q",
            volumes={tmpdir: {"bind": "/workspace", "mode": "ro"}},
            working_dir="/workspace",
            mem_limit=MEMORY_LIMIT,
            network_mode="none",    # No external network access
            remove=True,            # Destroy container after run
            stdout=True,
            stderr=True,
            timeout=TIMEOUT_SECONDS,
        )

        output = result.decode("utf-8", errors="replace").strip()[-2000:]
        print(f"[validator] Tests PASSED")
        print(output[-300:])

        return {
            "validation_passed": True,
            "validation_error": None,
        }
        """
        
        # --- MVP SUBPROCESS IMPLEMENTATION ---
        import subprocess
        
        if req_content:
            print("[validator] Installing dependencies via subprocess...")
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt", "-q"],
                cwd=tmpdir,
                check=False
            )
            
        print(f"[validator] Running pytest on {test_path} via subprocess")
        try:
            result = subprocess.run(
                ["pytest", test_path, "-v", "--tb=short", "--no-header", "-q"],
                cwd=tmpdir,
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
