"""
fixer.py — LangGraph Fixer Node (libCST edition)

APPROACH:
  1. Parse the full test file with libCST (preserves formatting exactly)
  2. Extract the failing function's current code + module-level context
     (imports, fixtures) as LLM context
  3. Ask Groq to generate ONLY the replacement function — not the whole file
  4. Parse the LLM response with libCST to get a clean FunctionDef node
  5. Use a CSTTransformer to swap ONLY the target function's body
  6. Write the modified tree back — every untouched line is byte-for-byte identical

WHY libCST NOT FULL-FILE REWRITE:
  LLMs hallucinate imports, drop comments, reformat whitespace, and rename
  variables. Rewriting the whole file is noisy and destroys trust. libCST
  surgically patches only the one function that failed — nothing else changes.

FALLBACK:
  If libCST parsing fails (malformed file, unusual syntax), we fall back to
  full-file rewrite so the system still produces a result.
"""
import difflib
from typing import Optional

import libcst as cst

from langchain_core.runnables import RunnableConfig
from agent.state import AgentState


# ── libCST helpers ────────────────────────────────────────────────────────────

class FunctionReplacer(cst.CSTTransformer):
    """
    Traverses a module and replaces the body (and return annotation) of a
    specific function by name. Everything else — decorators, other functions,
    imports, comments, blank lines — is left exactly as-is.
    """
    def __init__(self, target_name: str, new_func: cst.FunctionDef):
        self.target_name = target_name
        self.new_func    = new_func
        self.replaced    = False

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if updated_node.name.value == self.target_name:
            self.replaced = True
            # Keep decorators, name, params from original.
            # Replace only the body and return type annotation.
            return updated_node.with_changes(
                body=self.new_func.body,
                returns=self.new_func.returns,
            )
        return updated_node


def _extract_function_code(module: cst.Module, func_name: str) -> Optional[str]:
    """Returns the source code of a named function, including class methods."""
    for node in module.body:
        if isinstance(node, cst.FunctionDef) and node.name.value == func_name:
            return module.code_for_node(node)
        if isinstance(node, cst.ClassDef):
            for item in node.body.body:
                if isinstance(item, (cst.FunctionDef,)) and item.name.value == func_name:
                    return module.code_for_node(item)
    return None


def _extract_module_context(module: cst.Module, exclude_func: str) -> str:
    """
    Extracts imports and pytest fixture functions (excluding the target function)
    to give the LLM visibility into what names are available in the module.
    """
    parts = []
    for node in module.body:
        if isinstance(node, cst.SimpleStatementLine):
            stmt = node.body[0]
            if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                parts.append(module.code_for_node(node).strip())
        elif isinstance(node, cst.FunctionDef) and node.name.value != exclude_func:
            is_fixture = any(
                (isinstance(d.decorator, cst.Attribute)
                 and hasattr(d.decorator.attr, "value")
                 and d.decorator.attr.value == "fixture")
                or
                (isinstance(d.decorator, cst.Name)
                 and d.decorator.value == "fixture")
                for d in node.decorators
            )
            if is_fixture:
                parts.append(module.code_for_node(node).strip())
    return "\n\n".join(parts)


def _extract_replacement_func(llm_code: str, func_name: str) -> Optional[cst.FunctionDef]:
    """
    Parses the LLM's response and finds the replacement FunctionDef node.
    Strips accidental markdown fences before parsing.
    """
    code = llm_code.strip()
    # Strip markdown code fences if present
    if code.startswith("```"):
        lines = code.splitlines()
        code = "\n".join(lines[1:])
        if code.rstrip().endswith("```"):
            code = "\n".join(code.splitlines()[:-1])

    try:
        replacement_module = cst.parse_module(code)
    except cst.ParserSyntaxError:
        return None

    # Search top-level and inside a wrapping class
    for node in replacement_module.body:
        if isinstance(node, cst.FunctionDef) and node.name.value == func_name:
            return node
    return None


# ── LLM prompt ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert software engineer fixing a failing pytest test function.

Your job: return ONLY the corrected function definition. Nothing else.

Rules:
1. Return ONLY the complete function — starting with `def` (or decorators if any), ending with the last line of the body.
2. Do NOT include any other functions, imports, or module-level code.
3. Fix ONLY what's needed to make the test pass with the current application code.
4. Preserve the original function signature (name, parameters) exactly.
5. Match the existing code style (spacing, naming, comments).
6. No explanation, no markdown, no code fences."""


def _build_prompt(
    func_name: str,
    current_func_code: str,
    module_context: str,
    source_content: str,
    assertion_error: str,
    user_hint: str,
    source_path: str,
) -> str:
    hint_section = f"\n## Developer Hint\n{user_hint}" if user_hint else ""
    return f"""Fix this failing pytest function: `{func_name}`

## Assertion Error
```
{assertion_error}
```

## Current Function (needs fixing)
```python
{current_func_code}
```

## Module Context (imports and fixtures available)
```python
{module_context or "# (none)"}
```

## Application Source File ({source_path})
```python
{source_content[:4000]}
```
{hint_section}

Return ONLY the corrected function definition. Start with `def {func_name}` (or its decorator). No other code."""


# ── Diff helper ───────────────────────────────────────────────────────────────

def _compute_diff(original: str, patched: str, filename: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "\n".join(diff)


# ── Node ──────────────────────────────────────────────────────────────────────

def fixer_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    LangGraph node: generates a patched test file using libCST + Groq.

    Primary path: surgical libCST patch of the failing function only.
    Fallback path: full-file rewrite (if libCST parsing fails).
    """
    settings = config["configurable"]["settings"]
    fi             = state.get("failure_info") or {}
    test_content   = state.get("test_file_content") or ""
    source_content = state.get("source_file_content") or ""
    user_hint      = state.get("user_hint") or ""
    test_path      = fi.get("test_file_path", "test_file.py")
    func_name      = fi.get("test_function_name", "")
    assertion_error = fi.get("assertion_error", "")
    source_path    = fi.get("source_file_path", "unknown")

    client = config["configurable"]["groq_client"]

    # ── Primary path: libCST surgical patch ──────────────────────────────────
    cst_error = None
    if func_name and test_content:
        try:
            module = cst.parse_module(test_content)
            current_func_code = _extract_function_code(module, func_name)
            module_context    = _extract_module_context(module, func_name)

            if current_func_code:
                prompt = _build_prompt(
                    func_name=func_name,
                    current_func_code=current_func_code,
                    module_context=module_context,
                    source_content=source_content,
                    assertion_error=assertion_error,
                    user_hint=user_hint,
                    source_path=source_path,
                )

                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1024,
                )

                llm_output = response.choices[0].message.content or ""
                replacement_func = _extract_replacement_func(llm_output, func_name)

                if replacement_func:
                    replacer = FunctionReplacer(func_name, replacement_func)
                    patched_module = module.visit(replacer)

                    if replacer.replaced:
                        patched = patched_module.code
                        patch_diff = _compute_diff(test_content, patched, test_path)
                        print(f"[fixer] libCST patch applied to {func_name}")
                        return {
                            "patched_test_file": patched,
                            "patch_diff": patch_diff,
                        }
                    else:
                        cst_error = f"FunctionReplacer: '{func_name}' not found in module"
                else:
                    cst_error = "LLM response did not contain a valid function definition"
            else:
                cst_error = f"Function '{func_name}' not found in test file"

        except Exception as e:
            cst_error = f"libCST error: {e}"

    print(f"[fixer] libCST path failed ({cst_error}), falling back to full-file rewrite")

    # ── Fallback: full-file rewrite ───────────────────────────────────────────
    FALLBACK_SYSTEM = """You are an expert software engineer specializing in test maintenance.

Your job: rewrite a failing test file so all tests pass, while preserving the intent of each test.

Rules:
1. Return ONLY the complete Python file content — no markdown, no explanation, no code fences.
2. Fix ONLY what's needed to make tests pass.
3. Match the existing code style exactly.
4. Start your response with the first line of Python code."""

    fallback_prompt = f"""Rewrite the failing test file to make all tests pass.

## Failing Test File ({test_path})
```python
{test_content}
```

## Application Source File ({source_path})
```python
{source_content[:3000]}
```

## Assertion Error
```
{assertion_error}
```
{"## Developer Hint\n" + user_hint if user_hint else ""}

Return ONLY the complete corrected Python file. No explanation, no markdown fences."""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": FALLBACK_SYSTEM},
                {"role": "user",   "content": fallback_prompt},
            ],
            temperature=0.15,
            max_tokens=2048,
        )

        patched = response.choices[0].message.content.strip()

        # Strip accidental markdown fences
        if patched.startswith("```"):
            lines = patched.split("\n")
            patched = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        patch_diff = _compute_diff(test_content, patched, test_path)
        print(f"[fixer] Fallback full-file rewrite applied")
        return {
            "patched_test_file": patched,
            "patch_diff": patch_diff,
        }

    except Exception as e:
        return {
            "patched_test_file": None,
            "patch_diff":        None,
            "validation_error":  f"Fixer error: {str(e)[:200]}",
        }
