"""
graph.py — LangGraph Agent Graph (single unified graph with checkpointing)

ONE GRAPH WITH MemorySaver CHECKPOINTING:
  The original two-graph design (main + fix) manually serialized state to
  Supabase and reconstructed it on approval — fragile if schema evolves.

  Now we use a SINGLE graph with LangGraph's built-in MemorySaver checkpointer.
  Each pipeline run has a thread_id = run_id. The graph pauses at the HITL gate
  and resumes when the developer approves:

    graph.update_state(config, {"user_hint": hint})
    graph.invoke(None, config)   # continues from checkpoint

  This means state reconstruction is handled by LangGraph, not our code.

  NOTE: MemorySaver stores checkpoints in-memory (lost on restart).
  For production, install `langgraph-checkpoint-sqlite` and switch to SqliteSaver.

ROUTING:
  classify → TEST_MISMATCH + MANUAL   → hitl_gate → [PAUSE] → fix
           → TEST_MISMATCH + AUTOPILOT → fix (no pause)
           → anything else             → stop → END

  interrupt_before=["fix"] only applies when reached via the MANUAL path
  because AUTOPILOT routes directly to "auto_fix" (a separate node alias
  that is NOT in interrupt_before).
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from agent.state import AgentState
from agent.nodes.fetcher    import fetcher_node
from agent.nodes.classifier import classifier_node
from agent.nodes.stopper    import stopper_node
from agent.nodes.fixer      import fixer_node
from agent.nodes.validator  import validator_node
from agent.nodes.pr_creator import pr_creator_node


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_classify(state: AgentState) -> str:
    category = state.get("failure_category", "UNCLASSIFIABLE")
    mode     = state.get("mode", "MANUAL")

    if category != "TEST_MISMATCH":
        return "stop"
    if mode == "AUTOPILOT":
        return "auto_fix"   # bypasses interrupt_before=["fix"]
    return "hitl_gate"      # MANUAL: pauses before "fix"


# ── HITL Gate node ────────────────────────────────────────────────────────────

def hitl_gate_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Updates DB to WAITING_FOR_APPROVAL, persists file content so the
    dashboard can display context. The graph then pauses (interrupt_before=["fix"]).
    No state reconstruction needed — LangGraph checkpointer holds everything.
    """
    db = config["configurable"]["db"]

    run_id = state["run_id"]

    db.table("pipeline_runs").update({
        "status":                "WAITING_FOR_APPROVAL",
        "failure_category":      state.get("failure_category"),
        "classification_reason": state.get("classification_reason"),
        "test_file_content":     state.get("test_file_content"),
        "source_file_content":   state.get("source_file_content"),
    }).eq("id", run_id).execute()

    db.table("fix_history").insert({
        "run_id": run_id,
        "action": "CLASSIFIED",
        "actor":  "realive[bot]",
        "details": {
            "category": state.get("failure_category"),
            "reason":   state.get("classification_reason"),
        },
    }).execute()

    return {"run_id": run_id}  # Return run_id to satisfy LangGraph state update requirement


# ── Save-fix node (post-fixer) ────────────────────────────────────────────────

def save_fix_node(state: AgentState, config: RunnableConfig) -> dict:
    """Persists fixer output to Supabase. Status → VALIDATED or FIX_READY."""
    db = config["configurable"]["db"]

    run_id = state["run_id"]

    update_data = {
        "status": "FAILED",
        "validation_error": state.get("validation_error"),
    }

    if state.get("patched_test_file"):
        update_data["status"] = "VALIDATED" if state.get("validation_passed") is True else "VALIDATION_FAILED"
        update_data["patched_test_file"] = state.get("patched_test_file")
        update_data["patch_diff"] = state.get("patch_diff")
        update_data["validation_passed"] = state.get("validation_passed")

        db.table("fix_history").insert({
            "run_id": run_id,
            "action": "FIX_GENERATED",
            "actor":  "realive[bot]",
            "details": {"diff_length": len(state.get("patch_diff") or "")},
        }).execute()

    db.table("pipeline_runs").update(update_data).eq("id", run_id).execute()

    return {"run_id": run_id}


# ── Retry Gate node ───────────────────────────────────────────────────────────

def retry_gate_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Graph pauses here after validation fails (interrupt_before=["retry_gate"]).
    Developer can provide a new hint and click Retry.
    """
    return {"run_id": state["run_id"]}


# ── Routing Post-Validation ───────────────────────────────────────────────────

def route_after_save_fix(state: AgentState) -> str:
    if state.get("validation_passed") is True:
        return "create_pr"
    return "retry_gate"

def route_after_auto_save_fix(state: AgentState) -> str:
    if state.get("validation_passed") is True:
        return "auto_create_pr"
    return "stop"  # In autopilot, if it fails, we just stop (no retry loop yet)


# ── Graph factory ─────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Builds the unified LangGraph with two fix paths:
      - hitl_gate → [interrupt] → fix   (MANUAL mode)
      - auto_fix                          (AUTOPILOT mode, same function, different node name)

    interrupt_before=["fix"] only pauses the MANUAL path.
    """
    builder = StateGraph(AgentState)

    builder.add_node("fetch_files", fetcher_node)
    builder.add_node("classify",    classifier_node)
    builder.add_node("stop",        stopper_node)
    builder.add_node("hitl_gate",   hitl_gate_node)
    builder.add_node("fix",         fixer_node)         # MANUAL: paused before this
    builder.add_node("auto_fix",    fixer_node)         # AUTOPILOT: no pause
    builder.add_node("validate",    validator_node)
    builder.add_node("auto_validate", validator_node)
    builder.add_node("save_fix",    save_fix_node)
    builder.add_node("auto_save_fix", save_fix_node)
    builder.add_node("retry_gate",  retry_gate_node)
    builder.add_node("create_pr",   pr_creator_node)
    builder.add_node("auto_create_pr", pr_creator_node)

    builder.set_entry_point("fetch_files")
    builder.add_edge("fetch_files", "classify")
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {"stop": "stop", "hitl_gate": "hitl_gate", "auto_fix": "auto_fix"},
    )

    # MANUAL path (pauses before "fix" via interrupt_before)
    builder.add_edge("hitl_gate",  "fix")
    builder.add_edge("fix",        "validate")
    builder.add_edge("validate",   "save_fix")
    builder.add_conditional_edges("save_fix", route_after_save_fix, {
        "create_pr": "create_pr",
        "retry_gate": "retry_gate"
    })
    builder.add_edge("retry_gate", "fix")  # The loop!
    builder.add_edge("create_pr",  END)

    # AUTOPILOT path (runs straight through)
    builder.add_edge("auto_fix",        "auto_validate")
    builder.add_edge("auto_validate",   "auto_save_fix")
    builder.add_conditional_edges("auto_save_fix", route_after_auto_save_fix, {
        "auto_create_pr": "auto_create_pr",
        "stop": "stop"
    })
    builder.add_edge("auto_create_pr",  END)

    builder.add_edge("stop", END)

    if checkpointer:
        return builder.compile(
            checkpointer=checkpointer,
            interrupt_after=["hitl_gate", "retry_gate"],   # Pauses after gates
        )
    return builder.compile()


# ── Singleton with checkpointer ───────────────────────────────────────────────

_checkpointer = MemorySaver()
realive_graph = build_graph(checkpointer=_checkpointer)


def get_checkpointer() -> MemorySaver:
    """Returns the shared checkpointer instance. Used by the approve endpoint."""
    return _checkpointer
