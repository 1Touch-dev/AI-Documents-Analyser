# MCP (Model Context Protocol) Integration Layer

This directory prepares the AI Document Analyser's Skills System for
integration with external orchestration tools such as **n8n**, **LangGraph**,
and any MCP-compatible agent platform.

---

## What are Skills?

Skills are **callable, structured AI workflows** that accept a JSON input,
call GPT, and return a deterministic JSON output.  They live in
`backend/skills/` and are routed by `backend/skills/skill_router.py`.

| Skill | Input | Output |
|---|---|---|
| `financial_analysis` | `document_text` or `context` | revenue breakdown, expense breakdown, insights, risk flags |
| `report_generation` | `context` or `document_text` | title, executive summary, metrics, findings, recommendations |
| `consulting_insights` | `context` or `document_text` | SWOT analysis, strategic priorities, overall assessment |

---

## How MCP Will Expose Skills as Tools

Each skill maps directly to an MCP **tool definition**:

```json
{
  "name": "financial_analysis",
  "description": "Extract structured financial data from document text.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "document_text": { "type": "string" },
      "model": { "type": "string", "default": "auto" }
    },
    "required": []
  }
}
```

The `skills_mcp.py` file in this directory implements the MCP server stub
that exposes all skills as tools over stdio (JSON-RPC 2.0).

---

## External Integration (n8n / Zapier / LangGraph)

Skills are already accessible over HTTP via:

```
POST /api/skills/run
{
  "skill": "financial_analysis",
  "input": { "document_text": "..." }
}
```

This endpoint can be called directly from any HTTP-capable orchestration
platform without MCP.  MCP adds **tool discovery** and **structured
argument validation** on top of the same underlying skill logic.

---

## Roadmap

- [x] Register skills as MCP tools via `server.py`
- [x] Implement JSON-RPC 2.0 tool execution via `POST /api/mcp/execute`
- [x] Enforce RBAC on MCP tool calls
- [ ] Connect MCP server to external orchestrators (n8n, LangGraph)
- [ ] Add skill chaining (output of one skill feeds another)
- [ ] Add streaming support for long-running report generation
