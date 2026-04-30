"""
MCP (Model Context Protocol) server stub for the Skills System.

This module exposes the three AI skills as MCP tools so they can be
discovered and invoked by any MCP-compatible agent (e.g. Claude Desktop,
Cursor Background Agent, n8n via MCP connector).

Usage (stdio transport – standard MCP pattern):
    python -m backend.mcp.skills_mcp

The server reads JSON-RPC 2.0 messages from stdin and writes responses to
stdout, following the MCP specification.

NOTE: This is a self-contained stub that calls the skills over HTTP so it
can run independently of the FastAPI process.  Set SKILLS_API_URL to point
at your deployed backend (default: http://localhost:8000).
"""

from __future__ import annotations

import json
import os
import sys
import logging
import requests
from typing import Any

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger(__name__)

SKILLS_API_URL = os.getenv("SKILLS_API_URL", "http://localhost:8000")

# ── MCP Tool Definitions ──────────────────────────────────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "name": "financial_analysis",
        "description": (
            "Extract structured financial insights from document text. "
            "Returns revenue breakdown, expense breakdown, key insights, risk flags, and summary."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "Raw document text to analyse. Leave empty to use indexed documents.",
                },
                "model": {
                    "type": "string",
                    "description": "GPT model to use (auto | gpt-4o | gpt-4.1 | gpt-4.1-mini).",
                    "default": "auto",
                },
            },
        },
    },
    {
        "name": "report_generation",
        "description": (
            "Generate a structured business report from document context. "
            "Returns title, executive summary, key metrics, findings, recommendations, and conclusion."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Document context for report generation. Leave empty to use indexed documents.",
                },
                "model": {
                    "type": "string",
                    "description": "GPT model to use.",
                    "default": "auto",
                },
            },
        },
    },
    {
        "name": "consulting_insights",
        "description": (
            "Apply a strategic consulting framework (SWOT + priorities) to document context. "
            "Returns strengths, weaknesses, opportunities, risks, strategic priorities, and overall assessment."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Document context for consulting analysis. Leave empty to use indexed documents.",
                },
                "model": {
                    "type": "string",
                    "description": "GPT model to use.",
                    "default": "auto",
                },
            },
        },
    },
]


# ── HTTP skill caller ─────────────────────────────────────────────────────────

def _call_skill(skill_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call the FastAPI /api/skills/run endpoint and return the result."""
    payload = {"skill": skill_name, "input": arguments}
    response = requests.post(
        f"{SKILLS_API_URL}/api/skills/run",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("result", {})


# ── JSON-RPC helpers ──────────────────────────────────────────────────────────

def _ok(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _write(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


# ── MCP request handlers ──────────────────────────────────────────────────────

def _handle(message: dict) -> dict | None:
    method = message.get("method", "")
    req_id = message.get("id")
    params = message.get("params", {})

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ai-documents-skills", "version": "1.0.0"},
        })

    if method == "tools/list":
        return _ok(req_id, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if tool_name not in {t["name"] for t in TOOLS}:
            return _err(req_id, -32602, f"Unknown tool: {tool_name}")
        try:
            result = _call_skill(tool_name, arguments)
            return _ok(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            })
        except Exception as exc:
            return _err(req_id, -32603, str(exc))

    if method == "notifications/initialized":
        return None  # No response for notifications

    return _err(req_id, -32601, f"Method not found: {method}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Run the MCP server on stdio (JSON-RPC 2.0)."""
    logger.info("MCP Skills Server starting (skills API: %s)", SKILLS_API_URL)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            _write(_err(None, -32700, f"Parse error: {exc}"))
            continue

        response = _handle(message)
        if response is not None:
            _write(response)


if __name__ == "__main__":
    main()
