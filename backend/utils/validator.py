"""
Input Validator
===============
Guards against prompt injection, oversized payloads, and malformed inputs
before they reach LLM calls or MCP tool execution.

Prompt injection patterns detected:
  - Role-switching attempts ("ignore previous instructions", "system:", "act as")
  - Jailbreak patterns ("DAN", "developer mode", "pretend you are")
  - Instruction override patterns ("<|im_start|>", "###SYSTEM###")
  - Data exfiltration patterns ("print your system prompt", "reveal instructions")
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ── Limits ────────────────────────────────────────────────────────────────────

MAX_DOCUMENT_TEXT_CHARS = 50_000
MAX_CONTEXT_CHARS = 20_000
MAX_QUERY_CHARS = 4_000
MAX_SKILL_INPUT_CHARS = 30_000

# ── Injection patterns ────────────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above|prior)\s+(instructions?|prompt|context)",
    r"(system|assistant)\s*:\s*you\s+are\s+now",
    r"act\s+as\s+(if\s+you\s+are\s+)?(a\s+)?(different|another|unrestricted|evil|jailbroken)",
    r"(developer|god|jailbreak|dan)\s+mode",
    r"pretend\s+(you\s+are|to\s+be)",
    r"forget\s+(everything|all)\s+(you|that)",
    r"<\|im_start\|>|<\|im_end\|>|<\|system\|>",
    r"###\s*system\s*###|###\s*instruction\s*###",
    r"(print|reveal|repeat|show|display|output)\s+(your\s+)?(system\s+)?(prompt|instruction|rules)",
    r"disregard\s+(your\s+)?(previous|all|prior)\s+(instructions?|training)",
    r"(you\s+are\s+)?(no\s+longer|not)\s+(bound\s+by|restricted\s+by|limited\s+to)",
    r"sudo\s+mode|root\s+mode|admin\s+override",
    r"jailbreak",
    r"bypass\s+(your\s+)?(safety|content|restriction)",
    r"<script\b|javascript:|data:text/html|onerror=|onload=",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS]


def _contains_injection(text: str) -> tuple[bool, str | None]:
    """Return (is_injected, matched_pattern_hint)."""
    for pattern in _COMPILED:
        m = pattern.search(text)
        if m:
            return True, m.group()[:80]
    return False, None


# ── Public validation functions ───────────────────────────────────────────────

class ValidationError(ValueError):
    """Raised when input fails validation. Message is safe to expose to callers."""


def validate_document_text(text: str, field: str = "document_text") -> str:
    """Validate and sanitise document text input."""
    if not isinstance(text, str):
        raise ValidationError(f"'{field}' must be a string.")
    text = text.strip()
    if len(text) > MAX_DOCUMENT_TEXT_CHARS:
        logger.warning("Input truncated from %d to %d chars", len(text), MAX_DOCUMENT_TEXT_CHARS)
        text = text[:MAX_DOCUMENT_TEXT_CHARS]
    injected, hint = _contains_injection(text)
    if injected:
        logger.warning("Prompt injection detected in '%s': %r", field, hint)
        raise ValidationError(
            f"Input rejected: potential prompt injection detected in '{field}'. "
            "Please provide clean document content."
        )
    return text


def validate_context(text: str, field: str = "context") -> str:
    """Validate context / query string."""
    if not isinstance(text, str):
        raise ValidationError(f"'{field}' must be a string.")
    text = text.strip()
    if len(text) > MAX_CONTEXT_CHARS:
        text = text[:MAX_CONTEXT_CHARS]
    injected, hint = _contains_injection(text)
    if injected:
        logger.warning("Prompt injection detected in '%s': %r", field, hint)
        raise ValidationError(
            f"Input rejected: potential prompt injection in '{field}'."
        )
    return text


def validate_workflow_input(input_data: dict) -> dict:
    """Validate and sanitise workflow input dict."""
    sanitised: dict = {}
    for key, val in input_data.items():
        if isinstance(val, str):
            if key in ("document_text", "context"):
                sanitised[key] = validate_document_text(val, field=key)
            else:
                sanitised[key] = validate_context(val, field=key)
        else:
            sanitised[key] = val  # non-string values (numbers, dicts) pass through
    return sanitised


def validate_mcp_arguments(tool_name: str, arguments: dict) -> dict:
    """Validate MCP tool call arguments. Raises ValidationError on failure."""
    # Ensure all string values are injection-free
    sanitised: dict = {}
    for key, val in arguments.items():
        if isinstance(val, str):
            sanitised[key] = validate_document_text(val, field=f"{tool_name}.{key}")
        else:
            sanitised[key] = val

    # Tool-specific required field checks
    if tool_name == "financial_analysis" and not sanitised.get("document_text", "").strip():
        sanitised["document_text"] = ""  # will fall back to vector store
    if tool_name in ("generate_report", "consulting_insights") and not sanitised.get("context", "").strip():
        sanitised["context"] = ""
    if tool_name == "run_workflow":
        wf = sanitised.get("workflow", "")
        if wf not in ("financial", "consulting", "report", ""):
            raise ValidationError(f"Unknown workflow '{wf}'. Must be: financial | consulting | report")

    return sanitised


def validate_provider(provider: str) -> str:
    allowed = {"openai", "bedrock"}
    if provider not in allowed:
        raise ValidationError(f"Invalid provider '{provider}'. Must be one of: {allowed}")
    return provider


def validate_export_format(fmt: str) -> str:
    allowed = {"json", "csv"}
    if fmt not in allowed:
        raise ValidationError(f"Invalid export format '{fmt}'. Must be 'json' or 'csv'.")
    return fmt
