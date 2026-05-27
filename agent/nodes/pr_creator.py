"""
pr_creator.py — LangGraph PR Creation Node

Opens a Fix PR targeting the original PR's head branch, not main.

Flow:
  1. Fetch the original PR's head branch (e.g. feature/payment-gateway)
  2. Create a new fix branch from that branch
  3. Commit the patched test file
  4. Open PR: realive/fix-<id> → feature/payment-gateway
  5. Record PR URL and update status to DELIVERED
"""
import uuid
from github import GithubException

from langchain_core.runnables import RunnableConfig
from agent.state import AgentState


def pr_creator_node(state: AgentState, config: RunnableConfig) -> dict:
    """LangGraph node: Creates a Pull Request with the validated patch."""
    db = config["configurable"]["db"]
    get_github_client = config["configurable"]["get_github_client"]
    run_id          = state["run_id"]
    repo_full_name  = state["repo_full_name"]
    patched_content = state.get("patched_test_file")
    pr_number       = state.get("pr_number", 0)

    fi        = state.get("failure_info") or {}
    test_path = fi.get("test_file_path", "tests/test.py")

    if not patched_content or state.get("validation_passed") is not True:
        return {"run_id": run_id}

    print(f"[pr_creator] Preparing to open PR for {repo_full_name} on {test_path}")

    try:
        gh   = get_github_client(repo_full_name)
        repo = gh.get_repo(repo_full_name)

        # ── 1. Determine base branch ─────────────────────────────────────────
        # Target the original PR's head branch, not main.
        # If the run was triggered by a direct push (pr_number=0), fall back to main.
        base_branch = "main"
        if pr_number and pr_number > 0:
            try:
                original_pr = repo.get_pull(pr_number)
                base_branch = original_pr.head.ref  # e.g. "feature/payment-gateway"
                print(f"[pr_creator] Base branch from PR #{pr_number}: {base_branch}")
            except Exception as e:
                print(f"[pr_creator] Could not fetch PR #{pr_number}, falling back to main: {e}")

        # ── 2. Create fix branch from base branch ────────────────────────────
        short_id    = str(uuid.uuid4())[:6]
        branch_name = f"realive/fix-{run_id[:8]}-{short_id}"

        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)
        print(f"[pr_creator] Created branch {branch_name} from {base_branch}")

        # ── 3. Commit the patched file to the fix branch ─────────────────────
        contents       = repo.get_contents(test_path, ref=branch_name)
        commit_message = f"fix(tests): update {test_path} [realive]"
        repo.update_file(
            path=test_path,
            message=commit_message,
            content=patched_content,
            sha=contents.sha,
            branch=branch_name,
        )
        print(f"[pr_creator] Committed patch to {branch_name}")

        # ── 4. Open Pull Request ─────────────────────────────────────────────
        pr_body = (
            f"🤖 **Automated test fix by [Realive](https://realive.app)**\n\n"
            f"**Failure Category**: `{state.get('failure_category', 'TEST_MISMATCH')}`\n"
            f"**Diagnosis**: {state.get('classification_reason', 'Test assertion outdated after application change.')}\n\n"
            f"The patch was validated — pytest passes with the updated test.\n\n"
            f"---\n_This PR was opened automatically. Review the diff before merging._"
        )

        pr = repo.create_pull(
            title=f"fix(tests): repair {test_path} [realive]",
            body=pr_body,
            head=branch_name,
            base=base_branch,   # ← correct: targets original PR branch
        )
        pr_url = pr.html_url
        print(f"[pr_creator] Opened Pull Request: {pr_url}")

        # ── 5. Update database ───────────────────────────────────────────────
        db.table("pipeline_runs").update({
            "status": "DELIVERED",
            "pr_url": pr_url,
        }).eq("id", run_id).execute()

        db.table("fix_history").insert({
            "run_id": run_id,
            "action": "PR_OPENED",
            "actor":  "realive[bot]",
            "details": {"pr_url": pr_url, "branch": branch_name, "base": base_branch},
        }).execute()

        return {"pr_url": pr_url}

    except GithubException as e:
        error_msg = f"GitHub API Error: {e.data.get('message', str(e))}"
        print(f"[pr_creator] {error_msg}")
        db.table("pipeline_runs").update({
            "status":           "VALIDATED",   # downgrade — patch is valid, PR just failed
            "validation_error": error_msg,
        }).eq("id", run_id).execute()
        return {"run_id": run_id}

    except Exception as e:
        print(f"[pr_creator] Error: {e}")
        return {"run_id": run_id}
