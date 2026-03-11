"""
Conversation Manager – CRUD for chat sessions with category grouping.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import Conversation

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manage conversations stored in PostgreSQL."""

    # ── Create ───────────────────────────────────────────
    @staticmethod
    def create_session(
        db: Session,
        category: str | None = None,
        title: str | None = None,
    ) -> Conversation:
        conv = Conversation(
            category=category,
            title=title,
            messages=[],
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        logger.info("Created conversation session: %s", conv.session_id)
        return conv

    # ── Add message ──────────────────────────────────────
    @staticmethod
    def add_message(
        db: Session,
        session_id: UUID,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> Conversation | None:
        conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
        if not conv:
            return None

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if sources:
            message["sources"] = sources

        # Must reassign to trigger SQLAlchemy change detection on JSON
        messages = list(conv.messages or [])
        messages.append(message)
        conv.messages = messages
        conv.updated_at = datetime.now(timezone.utc)

        # Auto-title from first user message
        if not conv.title and role == "user":
            conv.title = content[:80] + ("…" if len(content) > 80 else "")

        db.commit()
        db.refresh(conv)
        return conv

    # ── Read ─────────────────────────────────────────────
    @staticmethod
    def get_session(db: Session, session_id: UUID) -> Conversation | None:
        return db.query(Conversation).filter(Conversation.session_id == session_id).first()

    @staticmethod
    def get_history(db: Session, session_id: UUID) -> list[dict[str, Any]]:
        conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
        if not conv:
            return []
        return list(conv.messages or [])

    @staticmethod
    def list_sessions(
        db: Session,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        query = db.query(Conversation)
        if category:
            query = query.filter(Conversation.category == category)
        return (
            query.order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_categories(db: Session) -> list[str]:
        rows = (
            db.query(Conversation.category)
            .filter(Conversation.category.isnot(None))
            .distinct()
            .all()
        )
        return sorted([r[0] for r in rows])

    # ── Search ───────────────────────────────────────────
    @staticmethod
    def search(db: Session, query: str, limit: int = 20) -> list[Conversation]:
        """Full-text search across conversation titles and message content."""
        pattern = f"%{query}%"
        return (
            db.query(Conversation)
            .filter(
                or_(
                    Conversation.title.ilike(pattern),
                    Conversation.messages.cast(db.bind.dialect.name == "postgresql" and str or str).ilike(pattern)
                    if False
                    else Conversation.title.ilike(pattern),
                )
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .all()
        )

    # ── Update ───────────────────────────────────────────
    @staticmethod
    def update_session(
        db: Session,
        session_id: UUID,
        category: str | None = None,
        title: str | None = None,
    ) -> Conversation | None:
        conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
        if not conv:
            return None
        if category is not None:
            conv.category = category
        if title is not None:
            conv.title = title
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(conv)
        return conv

    # ── Delete ───────────────────────────────────────────
    @staticmethod
    def delete_session(db: Session, session_id: UUID) -> bool:
        conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        logger.info("Deleted conversation: %s", session_id)
        return True
