"""
Audit Logger
============
Writes structured audit records to the audit_logs DB table.

Every sensitive action (workflow run, MCP tool call, export, login, permission denial)
should produce an audit entry. Errors in audit logging are caught and warned — they
must never break the main request path.

Usage:
    from backend.services.audit_logger import audit_log

    audit_log(db, user=user, action="workflow_run", resource="financial",
              detail={"provider": "openai"}, request=request)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def audit_log(
    db,
    action: str,
    user=None,
    resource: str | None = None,
    detail: dict | None = None,
    request=None,
    status: str = "success",
) -> None:
    """
    Write a single audit record.

    Parameters
    ----------
    db       : SQLAlchemy Session
    action   : short action name, e.g. "workflow_run", "mcp_call", "login"
    user     : ORM User instance (optional — anon requests still logged)
    resource : the target resource or tool name
    detail   : arbitrary JSON-serialisable context dict
    request  : FastAPI Request (used to extract IP)
    status   : "success" | "denied" | "error"
    """
    try:
        from db.models import AuditLog

        ip = None
        if request is not None:
            ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or getattr(getattr(request, "client", None), "host", None)
            )

        record = AuditLog(
            user_id=getattr(user, "id", None),
            username=getattr(user, "username", None),
            action=action,
            resource=resource,
            detail=detail or {},
            ip_address=ip,
            status=status,
        )
        db.add(record)
        db.commit()
        logger.debug(
            "AUDIT [%s] %s → %s (user=%s ip=%s)",
            status, action, resource, getattr(user, "username", "anon"), ip,
        )
    except Exception as exc:
        logger.warning("Audit log write failed for action='%s': %s", action, exc)


def get_audit_trail(db, user=None, limit: int = 100, action_filter: str | None = None) -> list[dict]:
    """Return recent audit records. Admins see all; others see their own."""
    try:
        from db.models import AuditLog
        query = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        if user and getattr(user, "role", "user") != "admin":
            query = db.query(AuditLog).filter(
                AuditLog.username == user.username
            ).order_by(AuditLog.timestamp.desc()).limit(limit)
        if action_filter:
            query = query.filter(AuditLog.action == action_filter)
        records = query.all()
        return [
            {
                "id": str(r.id),
                "username": r.username,
                "action": r.action,
                "resource": r.resource,
                "status": r.status,
                "ip_address": r.ip_address,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "detail": r.detail,
            }
            for r in records
        ]
    except Exception as exc:
        logger.warning("Audit trail query failed: %s", exc)
        return []
