"""
classifier.py — LangGraph Classifier Node (Groq edition)

WHAT THIS NODE DOES:
Receives a parsed pytest failure and asks an LLM via Groq:
"Is this a test that needs updating, or a real application bug?"

WHY GROQ?
Groq runs open-source models (Llama 3) on custom LPU hardware — it's
the fastest LLM inference available, completely free (no card required),
and has a generous free tier: 14,400 requests/day.

HOW GROQ'S STRUCTURED OUTPUT WORKS:
We use Groq's JSON mode combined with a schema description in the prompt.
Groq returns valid JSON that we parse into our ClassificationResult Pydantic model.

CATEGORIES:
  TEST_MISMATCH    — App changed, test outdated. Fix the test. ✅
  APP_BUG          — Test is correct, app is broken. Alert dev. ❌
  ENV_CONFIG       — Import error, missing dependency, path issue. ❌
  FLAKY            — Timing/order-dependent failure. ❌
  UNCLASSIFIABLE   — Not enough info to decide. ❌
"""
import json
import time
from typing import Literal

from pydantic import BaseModel

from langchain_core.runnables import RunnableConfig
from agent.state import AgentState


# ── Pydantic schema for structured output ─────────────────────────────────────
class ClassificationResult(BaseModel):
    category: Literal[
        "TEST_MISMATCH",
        "APP_BUG",
        "ENV_CONFIG",
        "FLAKY",
        "UNCLASSIFIABLE"
    ]
    reason: str       # 1-2 sentence plain English explanation
    confidence: float # 0.0 → 1.0


# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior software engineer reviewing a CI test failure.

Classify the failure into exactly one category:

- TEST_MISMATCH: The application code was intentionally changed and the test
  assertion is now outdated. The test expectation needs updating.

- APP_BUG: The test assertion is correct and the application has a regression.
  The application code needs fixing, NOT the test.

- ENV_CONFIG: Import error, missing package, wrong path, or environment issue.

- FLAKY: Timing-dependent, network-dependent, or order-dependent failure.

- UNCLASSIFIABLE: Not enough information to decide confidently.

Respond with ONLY valid JSON matching this exact schema:
{
  "category": "<one of the five categories above>",
  "reason": "<1-2 sentence explanation>",
  "confidence": <float between 0.0 and 1.0>
}

Be conservative: if unsure between TEST_MISMATCH and APP_BUG, choose APP_BUG.
Only choose TEST_MISMATCH if you are confident the application change was intentional."""


def _build_user_prompt(state: AgentState) -> str:
    """Builds the user prompt with all available context."""
    fi = state.get("failure_info", {}) or {}

    test_section = ""
    if state.get("test_file_content"):
        test_section = f"""
## Test File ({fi.get('test_file_path', 'unknown')})
```python
{state['test_file_content'][:3000]}
```"""

    source_section = ""
    if state.get("source_file_content"):
        source_section = f"""
## Source File ({fi.get('source_file_path', 'unknown')})
```python
{state['source_file_content'][:3000]}
```"""

    return f"""Classify this CI test failure.

## Repository
{state.get('repo_full_name', 'unknown')}

## Failing Test
- File: {fi.get('test_file_path', 'unknown')}
- Function: {fi.get('test_function_name', 'unknown')}
- Line: {fi.get('line_number', 'unknown')}

## Assertion Error
```
{fi.get('assertion_error', 'No error details')}
```
{test_section}
{source_section}

Respond with ONLY the JSON object, no other text."""


def classifier_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    LangGraph node: classifies the failure using Groq (Llama 3).

    Returns a dict that gets merged into the agent state.
    The graph router reads failure_category to decide the next node.
    """
    settings = config["configurable"]["settings"]
    client = config["configurable"]["groq_client"]
    user_prompt = _build_user_prompt(state)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                response_format={"type": "json_object"},  # Forces valid JSON output
                temperature=0.1,    # Low = deterministic classification
                max_tokens=256,     # Classification response is short
            )

            raw = response.choices[0].message.content
            result = ClassificationResult.model_validate_json(raw)

            return {
                "failure_category": result.category,
                "classification_reason": f"[{result.confidence:.0%} confidence] {result.reason}",
            }

        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "rate_limit" in err_str.lower()

            if is_rate_limit and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)
                print(f"[classifier] Rate limited (attempt {attempt+1}). Waiting {wait}s...")
                time.sleep(wait)
                continue

            # Non-retryable or all retries exhausted — fail gracefully
            return {
                "failure_category": "UNCLASSIFIABLE",
                "classification_reason": f"Classifier error: {err_str[:200]}",
            }
