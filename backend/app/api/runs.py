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

from fastapi import APIRouter, HTTPException
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
def list_runs(limit: int = 20):
    """Returns the most recent pipeline runs, newest first."""
    result = db.table("pipeline_runs").select(
        "id, repo_full_name, pr_number, commit_sha, status, "
        "failure_category, classification_reason, created_at"
    ).order("created_at", desc=True).limit(limit).execute()
    return {"runs": result.data}


# ── GET /api/runs/{run_id} ────────────────────────────────────────────────────
@router.get("/runs/{run_id}", tags=["Runs"])
def get_run(run_id: str):
    """Returns full details of a single pipeline run including the patch diff."""
    result = db.table("pipeline_runs").select("*").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return result.data[0]


# ── POST /api/runs/{run_id}/approve ──────────────────────────────────────────
class ApproveRequest(BaseModel):
    hint: Optional[str] = None   # Optional developer context hint


@router.post("/runs/{run_id}/approve", tags=["Runs"])
async def approve_run(run_id: str, body: ApproveRequest):
    """
    Developer approves the classifier's TEST_MISMATCH decision.

    Resumes the paused LangGraph from its checkpoint, injecting the
    developer's optional hint into state. No state reconstruction needed.
    """
    result = db.table("pipeline_runs").select("id, status").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run = result.data[0]
    if run["status"] != "WAITING_FOR_APPROVAL":
        raise HTTPException(
            status_code=400,
            detail=f"Run is in status '{run['status']}' — can only approve WAITING_FOR_APPROVAL runs.",
        )

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

            # Inject user_hint into the checkpoint state, then resume
            await run_in_threadpool(
                realive_graph.update_state,
                graph_config,
                {"user_hint": body.hint},
            )
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
async def retry_run(run_id: str, body: ApproveRequest):
    """
    Developer requests a retry after validation failed.
    Resumes the graph from the retry_gate.
    """
    result = db.table("pipeline_runs").select("id, status").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run = result.data[0]
    if run["status"] not in ("VALIDATION_FAILED", "FIX_READY"):
        raise HTTPException(
            status_code=400,
            detail=f"Run is in status '{run['status']}' — can only retry VALIDATION_FAILED runs.",
        )

    db.table("pipeline_runs").update({"status": "FIXING", "user_hint": body.hint}).eq("id", run_id).execute()
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

            # Inject user_hint into the checkpoint state, then resume
            await run_in_threadpool(
                realive_graph.update_state,
                graph_config,
                {"user_hint": body.hint, "retry_count": 1}, # Increment or set retry count
            )
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
def reject_run(run_id: str):
    """Developer rejects the fix. Run is closed with no code changes."""
    result = db.table("pipeline_runs").select("id, status").eq("id", run_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    db.table("pipeline_runs").update({"status": "REJECTED"}).eq("id", run_id).execute()
    db.table("fix_history").insert({
        "run_id": run_id,
        "action": "REJECTED",
        "actor":  "developer",
        "details": {},
    }).execute()

    return {"run_id": run_id, "status": "REJECTED"}

