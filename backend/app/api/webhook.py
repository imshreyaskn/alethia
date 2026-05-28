"""
webhook.py — GitHub Webhook Receiver

WHAT IS A WEBHOOK?
A webhook is GitHub saying "something just happened — here's the data."
Instead of your server asking GitHub "did anything happen?" every 5 seconds
(polling), GitHub pushes the event to you the moment it occurs.

For Realive, we configure GitHub Actions to POST to this endpoint when a
CI run fails. The payload contains the repo, commit SHA, PR number, and
the raw pytest output.

SIGNATURE VERIFICATION — why it matters:
Anyone on the internet can POST to your public webhook URL. Without
verification, a bad actor could send fake "CI failed" payloads and trick
Realive into doing things.

GitHub signs every webhook with HMAC-SHA256 using your webhook secret.
We recompute the signature from the raw body and compare. If they don't
match, we reject the request with 403.

HMAC (Hash-based Message Authentication Code):
Think of it like a wax seal on a letter. Only someone with the secret key
can produce the correct seal. We verify the seal before opening the letter.
"""
import hashlib
import hmac
import uuid
import asyncio

from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.log_parser import parse_pytest_output, _guess_source_file_candidates
from app.db.client import db
from app.github.auth import get_github_client, fetch_file_content
from groq import Groq

router = APIRouter()
groq_client = Groq(api_key=settings.GROQ_API_KEY)


# ── Request Body Schema ───────────────────────────────────────────────────────
class WebhookPayload(BaseModel):
    """
    The JSON body we expect from GitHub Actions when CI fails.
    
    The GitHub Actions workflow (set up in the test repo) will POST this
    after a pytest run fails. We define the shape with Pydantic so FastAPI
    validates it automatically — wrong field types = 422 error before our
    code even runs.
    """
    repository: str       # "imshreyaskn/realive-test-target"
    pr_number: int        # Pull request number (0 for direct pushes)
    commit_sha: str       # The git commit that triggered CI
    ci_log: str           # Raw pytest --tb=short output
    mode: Optional[str] = "MANUAL"  # MANUAL or AUTOPILOT


# ── Signature Verification ────────────────────────────────────────────────────
def verify_github_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    Verifies the X-Hub-Signature-256 header GitHub sends with every webhook.
    
    The algorithm:
    1. Compute HMAC-SHA256 of the raw request body using our webhook secret
    2. Compare to the signature GitHub sent
    3. Use hmac.compare_digest() — constant time comparison to prevent
       timing attacks (don't use == for secrets!)

    Args:
        raw_body:         The raw bytes of the request body
        signature_header: The "sha256=abc123..." header value from GitHub

    Returns:
        True if valid, False if tampered or wrong secret
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_sig = "sha256=" + hmac.new(
        key=settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, signature_header)


# ── Webhook Endpoint ──────────────────────────────────────────────────────────
@router.post("/webhook/github", tags=["Webhook"])
async def receive_github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
):
    """
    Receives CI failure notifications from GitHub Actions.
    
    Flow:
    1. Verify the request is genuinely from GitHub (HMAC signature check)
    2. Parse the raw pytest log → structured failure info
    3. Create a pipeline_run record in Supabase (status: CLASSIFYING)
    4. Return the run_id so the caller knows we've logged it
    
    The LangGraph agent (Milestone 4) will pick up from status=CLASSIFYING
    and run the classifier node.
    """

    # Step 1: Read raw body BEFORE parsing JSON
    # We need raw bytes for signature verification — once parsed to JSON,
    # the original byte sequence may differ (key ordering, whitespace, etc.)
    raw_body = await request.body()

    # Step 2: Verify signature
    if settings.GITHUB_WEBHOOK_SECRET:
        if not verify_github_signature(raw_body, x_hub_signature_256 or ""):
            raise HTTPException(
                status_code=403,
                detail="Invalid webhook signature. Check GITHUB_WEBHOOK_SECRET in .env."
            )

    # Step 3: Parse JSON body into our schema
    try:
        import json
        body_dict = json.loads(raw_body)
        payload = WebhookPayload(**body_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    # Step 4: Parse the pytest log (returns a list of ParsedFailure)
    parsed_failures = parse_pytest_output(payload.ci_log)
    if not parsed_failures:
        # If we couldn't parse the log, we still create a single record — 
        # the classifier will handle the "unclassifiable" case.
        parsed_failures = [None]

    created_runs = []
    
    for parsed_failure in parsed_failures:
        # Step 5: Build the failure_info JSON for the DB
        failure_info = None
        if parsed_failure:
            failure_info = {
                "test_file_path":      parsed_failure.test_file_path,
                "test_function_name":  parsed_failure.test_function_name,
                "line_number":         parsed_failure.line_number,
                "assertion_error":     parsed_failure.assertion_error,
                "source_file_path":    parsed_failure.source_file_path,
            }

        # Step 6: Smart Idempotency & Deduplication Check
        # We find recent runs for this repository (ignoring commit_sha)
        existing = db.table("pipeline_runs").select("id, status, failure_info, pr_url").eq(
            "repo_full_name", payload.repository
        ).order("created_at", desc=True).limit(50).execute()
        
        existing_run_id = None
        for run in existing.data:
            run_fi = run.get("failure_info")
            
            # Match if both are unparseable
            if failure_info is None and run_fi is None:
                if run.get("status") not in ("STOPPED", "FAILED", "DELIVERED", "REJECTED"):
                    existing_run_id = run["id"]
                    break
            
            # Match exact test failure signature
            elif failure_info and run_fi:
                same_test = failure_info.get("test_function_name") == run_fi.get("test_function_name")
                same_error = failure_info.get("assertion_error") == run_fi.get("assertion_error")
                
                if same_test and same_error:
                    status = run.get("status")
                    if status not in ("STOPPED", "FAILED", "DELIVERED", "REJECTED"):
                        # We are actively working on this EXACT failure right now.
                        existing_run_id = run["id"]
                        break
                    elif status == "DELIVERED" and run.get("pr_url"):
                        # We already created a PR for this exact failure! Is it still open?
                        try:
                            pr_url = run.get("pr_url")
                            if "/pull/" in pr_url:
                                pr_num = int(pr_url.split("/pull/")[-1].split("/")[0]) # Extract PR number cleanly
                                gh = get_github_client(payload.repository)
                                repo_obj = gh.get_repo(payload.repository)
                                pr = repo_obj.get_pull(pr_num)
                                if pr.state == "open":
                                    print(f"[webhook] Deduplicated: PR #{pr_num} is still open for {failure_info.get('test_function_name')}.")
                                    existing_run_id = run["id"]
                                    break
                        except Exception as e:
                            print(f"[webhook] Failed to check PR status for deduplication: {e}")
                            pass
                            
        if existing_run_id:
            created_runs.append({
                "run_id": existing_run_id,
                "status": "DUPLICATE",
                "parsed": failure_info is not None,
                "failure_info": failure_info,
            })
            continue

        # Step 7: Write pipeline_run to Supabase
        run_id = str(uuid.uuid4())
        db_record = {
            "id":              run_id,
            "repo_full_name":  payload.repository,
            "pr_number":       payload.pr_number,
            "commit_sha":      payload.commit_sha,
            "status":          "CLASSIFYING",
            "failure_info":    failure_info,
            "mode":            payload.mode,
        }

        db.table("pipeline_runs").insert(db_record).execute()

        # Step 8: Write to audit log
        db.table("fix_history").insert({
            "run_id": run_id,
            "action": "WEBHOOK_RECEIVED",
            "actor":  "realive[bot]",
            "details": {
                "parsed_failure": failure_info,
                "raw_log_length": len(payload.ci_log),
            },
        }).execute()

        # Step 9: Kick off the LangGraph agent in a background thread.
        initial_state = {
            "run_id":                  run_id,
            "repo_full_name":          payload.repository,
            "pr_number":               payload.pr_number,
            "commit_sha":              payload.commit_sha,
            "raw_ci_log":              payload.ci_log,
            "mode":                    payload.mode or "MANUAL",
            "failure_info":            failure_info,
            "failure_category":        None,
            "classification_reason":   None,
            "stop_reason":             None,
            "test_file_content":       None,
            "source_file_content":     None,
            "user_hint":               None,
            "patched_test_file":       None,
            "patch_diff":              None,
            "validation_passed":       None,
            "validation_error":        None,
            "pr_url":                  None,
            "retry_count":             0,
        }

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

        from agent.graph import realive_graph

        async def run_graph(state=initial_state, conf=graph_config, rid=run_id):
            try:
                await run_in_threadpool(realive_graph.invoke, state, conf)
            except Exception as exc:
                print(f"[webhook] Agent crashed for run {rid}: {exc}")
                try:
                    db.table("pipeline_runs").update({
                        "status": "FAILED",
                        "validation_error": f"Agent error: {str(exc)[:300]}",
                    }).eq("id", rid).execute()
                except Exception:
                    pass

        asyncio.create_task(run_graph())
        
        created_runs.append({
            "run_id": run_id,
            "status": "CLASSIFYING",
            "parsed": failure_info is not None,
            "failure_info": failure_info,
        })

    return {
        "message": f"Processed {len(created_runs)} failures from CI log.",
        "runs": created_runs
    }

