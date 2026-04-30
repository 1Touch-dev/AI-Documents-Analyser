"""
Role-Based Access Control (RBAC)
=================================

Roles (stored in users.role):
  admin    — full access
  analyst  — workflows + skills + export + MCP (read/write)
  viewer   — read-only (list workflows/reports, query only)
  user     — legacy default = same as analyst

Permission matrix:
  Action              admin  analyst  viewer
  ─────────────────────────────────────────
  run_workflow        ✓      ✓        ✗
  run_skill           ✓      ✓        ✗
  mcp_execute         ✓      ✓        ✗
  export              ✓      ✓        ✗
  webhook_trigger     ✓      ✓        ✗
  save_report         ✓      ✓        ✗
  view_reports        ✓      ✓        ✓
  view_usage          ✓      ✓        ✓
  query_documents     ✓      ✓        ✓
  admin_ops           ✓      ✗        ✗

MCP tool permissions per role:
  admin    — all tools
  analyst  — financial_analysis, generate_report, consulting_insights, run_workflow
  viewer   — none (read-only, no tool execution)
"""

from __future__ import annotations

from fastapi import HTTPException

# ── Role definitions ──────────────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "run_workflow", "run_skill", "mcp_execute", "export",
        "webhook_trigger", "save_report", "view_reports", "view_usage",
        "query_documents", "admin_ops",
    },
    "analyst": {
        "run_workflow", "run_skill", "mcp_execute", "export",
        "webhook_trigger", "save_report", "view_reports", "view_usage",
        "query_documents",
    },
    "user": {  # legacy default — treated as analyst
        "run_workflow", "run_skill", "mcp_execute", "export",
        "webhook_trigger", "save_report", "view_reports", "view_usage",
        "query_documents",
    },
    "viewer": {
        "view_reports", "view_usage",
        # viewer cannot query documents — read-only access to saved reports and usage stats only
    },
}

MCP_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "admin":   {"financial_analysis", "generate_report", "consulting_insights", "run_workflow"},
    "analyst": {"financial_analysis", "generate_report", "consulting_insights", "run_workflow"},
    "user":    {"financial_analysis", "generate_report", "consulting_insights", "run_workflow"},
    "viewer":  set(),
}

ROLE_LABELS = {
    "admin":   "Administrator",
    "analyst": "Analyst",
    "user":    "Analyst (legacy)",
    "viewer":  "Read-only Viewer",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_role(user) -> str:
    """Safely return the role string, defaulting to 'user'."""
    return getattr(user, "role", None) or "user"


def has_permission(user, action: str) -> bool:
    """Return True if user's role allows the given action."""
    if user is None:
        return False
    role = _get_role(user)
    return action in ROLE_PERMISSIONS.get(role, set())


def can_use_mcp_tool(user, tool_name: str) -> bool:
    """Return True if user's role can call the MCP tool."""
    if user is None:
        return False
    role = _get_role(user)
    return tool_name in MCP_TOOL_PERMISSIONS.get(role, set())


def require_permission(user, action: str, detail: str | None = None) -> None:
    """
    Raise HTTP 403 if user lacks the required permission.
    Raise HTTP 401 if user is None (unauthenticated).
    """
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid Bearer token.",
        )
    if not has_permission(user, action):
        role = _get_role(user)
        raise HTTPException(
            status_code=403,
            detail=detail or f"Role '{role}' does not have permission for action '{action}'.",
        )


def require_mcp_tool(user, tool_name: str) -> None:
    """Raise HTTP 403 if user's role cannot call the MCP tool."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required for MCP tool execution.")
    if not can_use_mcp_tool(user, tool_name):
        role = _get_role(user)
        raise HTTPException(
            status_code=403,
            detail=f"Role '{role}' is not permitted to call MCP tool '{tool_name}'.",
        )


def get_role_info(user) -> dict:
    role = _get_role(user)
    return {
        "role": role,
        "label": ROLE_LABELS.get(role, role),
        "permissions": sorted(ROLE_PERMISSIONS.get(role, set())),
        "mcp_tools": sorted(MCP_TOOL_PERMISSIONS.get(role, set())),
    }
