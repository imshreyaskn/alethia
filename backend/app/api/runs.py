"""
runs.py — Pipeline Runs API

Endpoints for the dashboard and Human-in-the-Loop gate:

  GET  /api/runs                   List recent pipeline runs
  GET  /api/runs/{run_id}          Get full details of one run
  POST /api/runs/{run_id}/approve  Developer approves — triggers the fixer
  POST /api/runs/{run_id}/reject   Developer rejects — marks run as rejected

THE HITL GATE:
After the classifier says TEST_MISMATCH, the graph pauses (interrupt_before=["fix"])
and waits for a human to approve. On approval, we:
  1. Update the LangGraph checkpoint state with the developer's hint
  2. Resume the graph from the checkpoint (invoke with None input, same thread_id)

No manual state reconstruction — LangGraph handles state persistence.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import AuthenticatedUser, get_current_user
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from app.db.client import db
from app.core.config import settings
from app.core.log_parser import _guess_source_file_candidates
from app.github.auth import get_github_client, fetch_file_content
from groq import Groq

router = APIRouter()
groq_client = Groq(api_key=settings.GROQ_API_KEY)


# ── GET /api/runs ─────────────────────────────────────────────────────────────
@router.get("/runs", tags=["Runs"])
def list_runs(limit: int = 20, user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the most recent pipeline runs for the authenticated user, newest first."""
    if not user.allowed_repos:
        return {"runs": []}
    result = db.table("pipeline_runs").select(
        "id, repo_full_name, pr_number, commit_sha, status, "
        "failure_category, classification_reason, created_at"
    ).in_("repo_full_name", user.allowed_repos).order("created_at", desc=True).limit(limit).execute()
    return {"runs": result.data}


# ── GET /api/runs/{run_id} ────────────────────────────────────────────────────
@router.get("/runs/{run_id}", tags=["Runs"])
def get_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Returns full details of a single pipeline run including the patch diff."""
    result = db.table("pipeline_runs").select("*").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    run = result.data[0]
    if run["repo_full_name"] not in user.allowed_repos:
        raise HTTPException(status_code=403, detail="You do not have access to this run")
    return run


# ── POST /api/runs/{run_id}/approve ──────────────────────────────────────────
class ApproveRequest(BaseModel):
    hint: Optional[str] = None   # Optional developer context hint


@router.post("/runs/{run_id}/approve", tags=["Runs"])
async def approve_run(run_id: str, body: ApproveRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Developer approves the classifier's TEST_MISMATCH decision.

    Resumes the paused LangGraph from its checkpoint, injecting the
    developer's optional hint into state. No state reconstruction needed.
    """
    result = db.table("pipeline_runs").select("*").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run = result.data[0]
    if run["status"] != "WAITING_FOR_APPROVAL":
        raise HTTPException(
            status_code=400,
            detail=f"Run is in status '{run['status']}' — can only approve WAITING_FOR_APPROVAL runs.",
        )

    if run["repo_full_name"] not in user.allowed_repos:
        raise HTTPException(status_code=403, detail="You do not have access to this run")

    # Mark as in-progress
    db.table("pipeline_runs").update({"status": "FIXING", "user_hint": body.hint}).eq("id", run_id).execute()
    db.table("fix_history").insert({
        "run_id": run_id,
        "action": "APPROVED",
        "actor":  "developer",
        "details": {"hint": body.hint},
    }).execute()

    graph_config = {
        "configurable": {
            "thread_id": run_id,
            "db": db,
            "settings": settings,
            "get_github_client": get_github_client,
            "fetch_file_content": fetch_file_content,
            "_guess_source_file_candidates": _guess_source_file_candidates,
            "groq_client": groq_client,
        }
    }

    async def run_fixer():
        try:
            from agent.graph import realive_graph, get_checkpointer
            checkpointer = get_checkpointer()

            # If MemorySaver lost the state on restart, reconstruct it from DB
            current_state = realive_graph.get_state(graph_config)
            if not current_state.values.get("repo_full_name"):
                print(f"[runs] Checkpoint missing for {run_id}. Reconstructing state from DB...")
                db_state = {
                    "run_id": run_id,
                    "repo_full_name": run["repo_full_name"],
                    "pr_number": run["pr_number"],
                    "commit_sha": run["commit_sha"],
                    "raw_ci_log": "",
                    "mode": run.get("mode", "MANUAL"),
                    "failure_info": run.get("failure_info"),
                    "failure_category": run.get("failure_category"),
                    "classification_reason": run.get("classification_reason"),
                    "stop_reason": None,
                    "test_file_content": run.get("test_file_content"),
                    "source_file_content": run.get("source_file_content"),
                    "user_hint": body.hint,
                    "patched_test_file": run.get("patched_test_file"),
                    "patch_diff": run.get("patch_diff"),
                    "validation_passed": run.get("validation_passed"),
                    "validation_error": run.get("validation_error"),
                    "pr_url": run.get("pr_url"),
                    "retry_count": run.get("retry_count", 0) or 0
                }
                await run_in_threadpool(realive_graph.update_state, graph_config, db_state)
            else:
                await run_in_threadpool(realive_graph.update_state, graph_config, {"user_hint": body.hint})
            # invoke(None, config) resumes from checkpoint — no state dict needed
            await run_in_threadpool(realive_graph.invoke, None, graph_config)
        except Exception as exc:
            print(f"[runs] Fixer crashed for run {run_id}: {exc}")
            try:
                db.table("pipeline_runs").update({
                    "status": "FAILED",
                    "validation_error": f"Fixer error: {str(exc)[:300]}",
                }).eq("id", run_id).execute()
            except Exception:
                pass

    asyncio.create_task(run_fixer())
    return {"run_id": run_id, "status": "FIXING", "message": "Fixer started."}


# ── POST /api/runs/{run_id}/retry ──────────────────────────────────────────────
@router.post("/runs/{run_id}/retry", tags=["Runs"])
async def retry_run(run_id: str, body: ApproveRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Developer requests a retry after validation failed.
    Resumes the graph from the retry_gate.
    """
    result = db.table("pipeline_runs").select("*").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run = result.data[0]
    if run["status"] not in ("VALIDATION_FAILED", "FIX_READY"):
        raise HTTPException(
            status_code=400,
            detail=f"Run is in status '{run['status']}' — can only retry VALIDATION_FAILED runs.",
        )

    if run["repo_full_name"] not in user.allowed_repos:
        raise HTTPException(status_code=403, detail="You do not have access to this run")

    db.table("pipeline_runs").update({
        "status": "FIXING",
        "user_hint": body.hint,
        "validation_passed": None,
        "validation_error": None,
        "patched_test_file": None,
        "patch_diff": None
    }).eq("id", run_id).execute()
    db.table("fix_history").insert({
        "run_id": run_id,
        "action": "RETRY_REQUESTED",
        "actor":  "developer",
        "details": {"hint": body.hint},
    }).execute()

    graph_config = {
        "configurable": {
            "thread_id": run_id,
            "db": db,
            "settings": settings,
            "get_github_client": get_github_client,
            "fetch_file_content": fetch_file_content,
            "_guess_source_file_candidates": _guess_source_file_candidates,
            "groq_client": groq_client,
        }
    }

    async def run_fixer():
        try:
            from agent.graph import realive_graph, get_checkpointer
            checkpointer = get_checkpointer()

            # If MemorySaver lost the state on restart, reconstruct it from DB
            current_state = realive_graph.get_state(graph_config)
            if not current_state.values.get("repo_full_name"):
                print(f"[runs] Checkpoint missing for {run_id}. Reconstructing state from DB...")
                db_state = {
                    "run_id": run_id,
                    "repo_full_name": run["repo_full_name"],
                    "pr_number": run["pr_number"],
                    "commit_sha": run["commit_sha"],
                    "raw_ci_log": "",
                    "mode": run.get("mode", "MANUAL"),
                    "failure_info": run.get("failure_info"),
                    "failure_category": run.get("failure_category"),
                    "classification_reason": run.get("classification_reason"),
                    "stop_reason": None,
                    "test_file_content": run.get("test_file_content"),
                    "source_file_content": run.get("source_file_content"),
                    "user_hint": body.hint,
                    "patched_test_file": run.get("patched_test_file"),
                    "patch_diff": run.get("patch_diff"),
                    "validation_passed": run.get("validation_passed"),
                    "validation_error": run.get("validation_error"),
                    "pr_url": run.get("pr_url"),
                    "retry_count": 1
                }
                await run_in_threadpool(realive_graph.update_state, graph_config, db_state)
            else:
                current_retry = current_state.values.get("retry_count", 0) or 0
                await run_in_threadpool(realive_graph.update_state, graph_config, {"user_hint": body.hint, "retry_count": current_retry + 1})
            # invoke(None, config) resumes from checkpoint
            await run_in_threadpool(realive_graph.invoke, None, graph_config)
        except Exception as exc:
            print(f"[runs] Fixer crashed during retry for run {run_id}: {exc}")
            try:
                db.table("pipeline_runs").update({
                    "status": "FAILED",
                    "validation_error": f"Fixer error on retry: {str(exc)[:300]}",
                }).eq("id", run_id).execute()
            except Exception:
                pass

    asyncio.create_task(run_fixer())
    return {"run_id": run_id, "status": "FIXING", "message": "Retry started."}


# ── POST /api/runs/{run_id}/reject ────────────────────────────────────────────
@router.post("/runs/{run_id}/reject", tags=["Runs"])
def reject_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Developer rejects the fix. Run is closed with no code changes."""
    result = db.table("pipeline_runs").select("id, status, repo_full_name").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run = result.data[0]
    if run["repo_full_name"] not in user.allowed_repos:
        raise HTTPException(status_code=403, detail="You do not have access to this run")

    db.table("pipeline_runs").update({"status": "REJECTED"}).eq("id", run_id).execute()
    db.table("fix_history").insert({
        "run_id": run_id,
        "action": "REJECTED",
        "actor":  "developer",
        "details": {},
    }).execute()

    return {"run_id": run_id, "status": "REJECTED"}

