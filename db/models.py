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

    is_active = Column(Integer, default=1)  # 1=active, 0=disabled

    def __repr__(self) -> str:
        return f"<User {self.username!r} role={self.role!r}>"


# ──────────────────────────────────────────────────────────
# LLM Usage / Cost Tracking
# ──────────────────────────────────────────────────────────
class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    username = Column(String(128), nullable=True, index=True)
    provider = Column(String(32), nullable=False, default="openai")
    model = Column(String(128), nullable=False)
    action = Column(String(64), nullable=True)       # "query", "skill", "workflow", "mcp"
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(String(32), default="0.0000")  # stored as string to avoid float precision loss
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<LLMUsage {self.model!r} {self.total_tokens}tok>"


# ──────────────────────────────────────────────────────────
# Saved Reports
# ──────────────────────────────────────────────────────────
class SavedReport(Base):
    __tablename__ = "saved_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    username = Column(String(128), nullable=True, index=True)
    report_type = Column(String(32), nullable=False, index=True)  # financial | consulting | report
    title = Column(String(512), nullable=True)
    data = Column(JSON, nullable=False)              # full structured result
    model_used = Column(String(128), nullable=True)
    provider = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<SavedReport {self.report_type!r} by {self.username!r}>"


# ──────────────────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    username = Column(String(128), nullable=True, index=True)
    action = Column(String(128), nullable=False, index=True)
    resource = Column(String(128), nullable=True)    # endpoint or tool name
    detail = Column(JSON, nullable=True)             # extra context
    ip_address = Column(String(64), nullable=True)
    status = Column(String(16), default="success")  # success | denied | error
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action!r} by {self.username!r}>"
