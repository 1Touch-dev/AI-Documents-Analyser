"""
FastAPI dependency helpers for auth + RBAC.

Usage in endpoint:
    from backend.auth.dependencies import require_auth, require_role

    @app.post("/api/workflows/run")
    async def run_workflow(body: ..., user: User = Depends(require_auth)):
        ...

    @app.delete("/api/admin/...")
    async def admin_op(user: User = Depends(require_role("admin"))):
        ...
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.settings import settings
from db.database import get_db
from db.models import User


# ── Token extraction ──────────────────────────────────────────────────────────

def _extract_token(request: Request) -> str | None:
    """Pull Bearer token from Authorization header or akp_token cookie."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("akp_token")


def _decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def _lookup_user(payload: dict, db: Session) -> User | None:
    username = payload.get("sub")
    if not username:
        return None
    return db.query(User).filter(User.username == username, User.is_active == 1).first()


# ── Dependency: optional auth ─────────────────────────────────────────────────

def optional_auth(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Returns None if no/invalid token, User if valid. Endpoints work unauthenticated."""
    token = _extract_token(request)
    if not token:
        return None
    payload = _decode_token(token)
    if not payload:
        return None
    return _lookup_user(payload, db)


# ── Dependency: required auth ─────────────────────────────────────────────────

def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Raises HTTP 401 if not authenticated."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Authorization: Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = _lookup_user(payload, db)
    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated.")
    return user


# ── Dependency factory: require a specific role ───────────────────────────────

def require_role(*allowed_roles: str):
    """
    Dependency factory. Usage:

        @app.post("/admin/...")
        async def admin_ep(user: User = Depends(require_role("admin"))):
    """
    def _dep(user: User = Depends(require_auth)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' is not permitted. Required: {list(allowed_roles)}",
            )
        return user
    return _dep
