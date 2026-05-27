"""
stopper.py — LangGraph Stopper Node

When the classifier decides a failure is NOT a test mismatch (e.g. APP_BUG,
ENV_CONFIG, FLAKY), this node:
  1. Updates the pipeline_run status to STOPPED in Supabase
  2. Writes an audit entry to fix_history explaining why we stopped
  3. Returns the final state

The graph terminates after this node — no fix is attempted.
"""
from langchain_core.runnables import RunnableConfig
from agent.state import AgentState


def stopper_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    LangGraph node: marks the run as STOPPED and records the reason.

    Called when failure_category is anything other than TEST_MISMATCH.
    """
    db = config["configurable"]["db"]
    run_id   = state["run_id"]
    category = state.get("failure_category", "UNCLASSIFIABLE")
    reason   = state.get("classification_reason", "No reason provided.")

    stop_reason = f"{category}: {reason}"

    # Update the pipeline_run record
    db.table("pipeline_runs").update({
        "status":      "STOPPED",
        "failure_category":     category,
        "classification_reason": reason,
        "stop_reason": stop_reason,
    }).eq("id", run_id).execute()

    # Audit log
    db.table("fix_history").insert({
        "run_id":  run_id,
        "action":  "STOPPED",
        "actor":   "realive[bot]",
        "details": {"category": category, "reason": reason},
    }).execute()

    return {"stop_reason": stop_reason}
