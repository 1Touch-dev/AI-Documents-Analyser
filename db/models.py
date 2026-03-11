"""
SQLAlchemy ORM models for the AI Knowledge Platform.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID

from db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ──────────────────────────────────────────────────────────
# Document
# ──────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    title = Column(String(512), nullable=False, index=True)
    category = Column(String(128), nullable=True, index=True)
    uploaded_by = Column(String(128), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    source_path = Column(String(1024), nullable=False)  # S3 key
    file_type = Column(String(16), nullable=False)
    file_size = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    status = Column(
        Enum("processing", "ready", "failed", name="doc_status"),
        default="processing",
    )
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256

    def __repr__(self) -> str:
        return f"<Document {self.title!r} ({self.file_type})>"


# ──────────────────────────────────────────────────────────
# Prompt Template
# ──────────────────────────────────────────────────────────
class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    name = Column(String(256), nullable=False, unique=True, index=True)
    category = Column(String(128), nullable=True, index=True)
    template = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<PromptTemplate {self.name!r}>"


# ──────────────────────────────────────────────────────────
# Conversation
# ──────────────────────────────────────────────────────────
class Conversation(Base):
    __tablename__ = "conversations"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    title = Column(String(512), nullable=True)
    category = Column(String(128), nullable=True, index=True)
    messages = Column(JSON, default=list)  # [{role, content, timestamp, sources}]
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.session_id} – {self.category}>"


# ──────────────────────────────────────────────────────────
# User (for auth)
# ──────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    username = Column(String(128), nullable=False, unique=True, index=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), default="user")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"
