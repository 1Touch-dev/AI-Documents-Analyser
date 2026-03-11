"""
Prompt Template Manager – CRUD operations for prompt templates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from string import Template
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import PromptTemplate

logger = logging.getLogger(__name__)

# ── Built-in default templates ────────────────────────────
DEFAULT_TEMPLATES = [
    {
        "name": "Default RAG",
        "category": "general",
        "description": "Standard retrieval-augmented generation prompt.",
        "template": (
            "You are a helpful AI assistant. Use the following context to answer "
            "the user's question. If the answer is not found in the context, say "
            "so clearly.\n\n"
            "Context:\n${context}\n\n"
            "Question: ${question}\n\n"
            "Answer:"
        ),
    },
    {
        "name": "Executive Summary",
        "category": "reports",
        "description": "Generate a concise executive summary from documents.",
        "template": (
            "You are a senior analyst. Based on the following document excerpts, "
            "write a concise executive summary highlighting key findings, risks, "
            "and recommendations.\n\n"
            "Documents:\n${context}\n\n"
            "Executive Summary:"
        ),
    },
    {
        "name": "Comparative Analysis",
        "category": "analysis",
        "description": "Compare multiple topics or documents.",
        "template": (
            "You are an expert analyst. Using the provided context, perform a "
            "detailed comparison covering similarities, differences, strengths, "
            "and weaknesses.\n\n"
            "Context:\n${context}\n\n"
            "Topic: ${question}\n\n"
            "Comparative Analysis:"
        ),
    },
    {
        "name": "Data Extraction",
        "category": "data",
        "description": "Extract structured data from documents.",
        "template": (
            "You are a data extraction specialist. From the following context, "
            "extract structured data and present it as a JSON object or table.\n\n"
            "Context:\n${context}\n\n"
            "Extraction request: ${question}\n\n"
            "Structured Output:"
        ),
    },
]


class PromptManager:
    """Manage prompt templates stored in PostgreSQL."""

    # ── Create ───────────────────────────────────────────
    @staticmethod
    def create(
        db: Session,
        name: str,
        template: str,
        category: str | None = None,
        description: str | None = None,
    ) -> PromptTemplate:
        prompt = PromptTemplate(
            name=name,
            template=template,
            category=category,
            description=description,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        logger.info("Created prompt template: %s", name)
        return prompt

    # ── Read ─────────────────────────────────────────────
    @staticmethod
    def get_by_id(db: Session, prompt_id: UUID) -> PromptTemplate | None:
        return db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> PromptTemplate | None:
        return db.query(PromptTemplate).filter(PromptTemplate.name == name).first()

    @staticmethod
    def list_all(db: Session, category: str | None = None) -> list[PromptTemplate]:
        query = db.query(PromptTemplate)
        if category:
            query = query.filter(PromptTemplate.category == category)
        return query.order_by(PromptTemplate.created_at.desc()).all()

    # ── Update ───────────────────────────────────────────
    @staticmethod
    def update(
        db: Session,
        prompt_id: UUID,
        **kwargs: Any,
    ) -> PromptTemplate | None:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            return None
        for key, value in kwargs.items():
            if hasattr(prompt, key) and value is not None:
                setattr(prompt, key, value)
        db.commit()
        db.refresh(prompt)
        logger.info("Updated prompt template: %s", prompt.name)
        return prompt

    # ── Delete ───────────────────────────────────────────
    @staticmethod
    def delete(db: Session, prompt_id: UUID) -> bool:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            return False
        db.delete(prompt)
        db.commit()
        logger.info("Deleted prompt template: %s", prompt.name)
        return True

    # ── Render ───────────────────────────────────────────
    @staticmethod
    def render(template_str: str, context: dict[str, str]) -> str:
        """
        Render a prompt template with variables.
        Uses Python Template (``$variable`` or ``${variable}``).
        """
        tpl = Template(template_str)
        return tpl.safe_substitute(context)

    # ── Seed defaults ────────────────────────────────────
    @staticmethod
    def seed_defaults(db: Session) -> None:
        """Insert built-in prompt templates if they don't already exist."""
        for tpl in DEFAULT_TEMPLATES:
            existing = db.query(PromptTemplate).filter(PromptTemplate.name == tpl["name"]).first()
            if not existing:
                db.add(PromptTemplate(**tpl))
        db.commit()
        logger.info("Default prompt templates seeded.")
