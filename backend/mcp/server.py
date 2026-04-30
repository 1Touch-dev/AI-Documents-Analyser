"""
MCP Server — real JSON-RPC 2.0 tool execution.

Exposes all skills as callable tools via POST /api/mcp/execute.

Spec: https://spec.modelcontextprotocol.io/specification/

Supported methods:
  initialize          — handshake + capability negotiation
  tools/list          — enumerate available tools
  tools/call          — execute a tool by name with arguments
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Tool registry ─────────────────────────────────────────────────────────────
# Maps MCP tool names → (skill_function, description, input_schema)

TOOLS: dict[str, dict[str, Any]] = {
    "financial_analysis": {
        "description": "Extract structured financial data (revenue, expenses, margins, risks, opportunities) from document text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_text": {"type": "string", "description": "Raw document text to analyse"},
                "provider":      {"type": "string", "description": "LLM provider: openai | bedrock", "default": "openai"},
                "model":         {"type": "string", "description": "Model ID", "default": "gpt-4o"},
            },
            "required": ["document_text"],
        },
    },
    "generate_report": {
        "description": "Generate a structured executive report with title, summary, metrics, analysis, and recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "context":  {"type": "string", "description": "Business context or document text"},
                "provider": {"type": "string", "description": "LLM provider", "default": "openai"},
                "model":    {"type": "string", "description": "Model ID", "default": "gpt-4o"},
            },
            "required": ["context"],
        },
    },
    "consulting_insights": {
        "description": "Perform SWOT analysis and generate strategic action recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "context":  {"type": "string", "description": "Business context"},
                "provider": {"type": "string", "description": "LLM provider", "default": "openai"},
                "model":    {"type": "string", "description": "Model ID", "default": "gpt-4o"},
            },
            "required": ["context"],
        },
    },
    "run_workflow": {
        "description": "Execute a named multi-step workflow (financial | consulting | report) against indexed documents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow":       {"type": "string", "enum": ["financial", "consulting", "report"]},
                "document_text":  {"type": "string", "description": "Optional document text (uses vector store if omitted)"},
                "provider":       {"type": "string", "default": "openai"},
                "model":          {"type": "string", "default": "auto"},
            },
            "required": ["workflow"],
        },
    },
}

MCP_SERVER_INFO = {
    "name": "ai-knowledge-platform-mcp",
    "version": "1.0.0",
    "description": "MCP server for AI Knowledge Platform — exposes financial, consulting and reporting tools.",
}

MCP_CAPABILITIES = {
    "tools": {"listChanged": False},
}


# ── JSON-RPC helpers ──────────────────────────────────────────────────────────

def _ok(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str, data: Any = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = str(data)
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


# ── Request dispatcher ────────────────────────────────────────────────────────

async def handle_request(body: dict, llm_router, api_keys: dict | None = None) -> dict:
    """
    Dispatch a JSON-RPC 2.0 request to the appropriate handler.
    """
    rpc_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    if method == "initialize":
        return _ok(rpc_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": MCP_SERVER_INFO,
            "capabilities": MCP_CAPABILITIES,
        })

    if method == "tools/list":
        tools_list = [
            {
                "name": name,
                "description": meta["description"],
                "inputSchema": meta["inputSchema"],
            }
            for name, meta in TOOLS.items()
        ]
        return _ok(rpc_id, {"tools": tools_list})

    if method == "tools/call":
        tool_name = params.get("name") or params.get("tool_name", "")
        arguments = params.get("arguments") or params.get("input", {})

        if tool_name not in TOOLS:
            return _err(rpc_id, -32601, f"Tool '{tool_name}' not found. Available: {list(TOOLS.keys())}")

        try:
            result = await _execute_tool(tool_name, arguments, llm_router, api_keys)
            return _ok(rpc_id, {"content": [{"type": "text", "text": str(result)}], "result": result})
        except Exception as exc:
            logger.exception("MCP tool '%s' execution failed: %s", tool_name, exc)
            return _err(rpc_id, -32000, f"Tool execution failed: {exc}")

    return _err(rpc_id, -32601, f"Method not found: {method}")


async def _execute_tool(
    tool_name: str,
    arguments: dict,
    llm_router,
    api_keys: dict | None,
) -> dict:
    """Route a tool call to the correct skill/workflow function."""
    provider = arguments.get("provider", "openai")
    model = arguments.get("model", "auto")

    if tool_name == "financial_analysis":
        from backend.skills.financial_analysis import analyze_financials
        return await analyze_financials(
            document_text=arguments.get("document_text", ""),
            llm_router=llm_router,
            model=model,
            api_keys=api_keys,
            provider=provider,
        )

    if tool_name == "generate_report":
        from backend.skills.report_generation import generate_report
        return await generate_report(
            context=arguments.get("context", ""),
            llm_router=llm_router,
            model=model,
            api_keys=api_keys,
            provider=provider,
        )

    if tool_name == "consulting_insights":
        from backend.skills.consulting_insights import generate_consulting_insights
        return await generate_consulting_insights(
            context=arguments.get("context", ""),
            llm_router=llm_router,
            model=model,
            api_keys=api_keys,
            provider=provider,
        )

    if tool_name == "run_workflow":
        from backend.workflows.workflow_engine import run_workflow
        return await run_workflow(
            workflow_name=arguments.get("workflow", "financial"),
            input_data={"document_text": arguments.get("document_text", ""), "context": arguments.get("document_text", "")},
            llm_router=llm_router,
            provider=provider,
            model=model,
            api_keys=api_keys,
        )

    raise ValueError(f"Unhandled tool: {tool_name}")
