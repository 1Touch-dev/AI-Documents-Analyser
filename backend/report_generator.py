"""
Report Generator – produces structured reports from RAG query results.

Supports output in Markdown, structured tables, and JSON.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate structured reports from document queries."""

    def __init__(self, llm_router: LLMRouter) -> None:
        self.llm = llm_router

    async def generate(
        self,
        topic: str,
        context: str,
        report_type: str = "general",
        output_format: str = "markdown",
        model_name: str = "auto",
        api_keys: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a report from provided context.

        Parameters
        ----------
        topic : str
            The report subject / title.
        context : str
            Document excerpts to base the report on.
        report_type : str
            One of: ``general``, ``market_analysis``, ``financial_summary``,
            ``strategy_comparison``.
        output_format : str
            One of: ``markdown``, ``table``, ``json``.
        model_name : str
            LLM to use.

        Returns
        -------
        dict
            ``{"report", "format", "metadata"}``
        """
        resolved_model = self.llm.resolve_model(model_name, topic, api_keys)

        system_prompt = self._build_system_prompt(report_type, output_format)
        user_prompt = (
            f"Write a comprehensive {report_type.replace('_', ' ')} about the topic: '{topic}'\n\n"
            f"You must use ONLY the following source material to write the report. Do not add outside knowledge. Do not write an introduction about what you will do.\n\n"
            f"--- SOURCE MATERIAL ---\n{context}\n----------------------\n\n"
            f"FINAL REPORT:\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        report_content = await self.llm.generate(
            model_name=resolved_model,
            messages=messages,
            temperature=0.4,
            max_tokens=4096,
            api_keys=api_keys,
        )

        # Post-process based on output format
        if output_format == "json":
            report_content = self._ensure_json(report_content)
        elif output_format == "table":
            report_content = self._ensure_table(report_content)

        metadata = {
            "topic": topic,
            "report_type": report_type,
            "output_format": output_format,
            "model_used": resolved_model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "context_length": len(context),
        }

        logger.info("Report generated: %s (%s)", topic, report_type)

        return {
            "report": report_content,
            "format": output_format,
            "metadata": metadata,
        }

    # ── Private helpers ──────────────────────────────────
    @staticmethod
    def _build_system_prompt(report_type: str, output_format: str) -> str:
        base = "You are an analytical AI. Extract facts from the source material and output the final report directly. Skip pleasantries and meta-commentary."

        type_instructions = {
            "general": "Write a thorough analysis covering key findings, insights, and conclusions.",
            "market_analysis": (
                "Focus on market trends, competitive landscape, opportunities, "
                "and threats. Include data points and projections where available."
            ),
            "financial_summary": (
                "Focus on financial metrics, revenue analysis, cost breakdown, "
                "profitability, and financial health indicators."
            ),
            "strategy_comparison": (
                "Compare different strategies or approaches, listing pros/cons, "
                "feasibility, resource requirements, and recommendations."
            ),
        }

        format_instructions = {
            "markdown": "Format the output as clean Markdown with headers, bullet points, and emphasis.",
            "table": (
                "Format the output as Markdown tables where appropriate. "
                "Include a summary section in prose and detailed data in tables."
            ),
            "json": (
                "Return the output as a valid JSON object with keys: "
                '"title", "summary", "sections" (array of {heading, content}), '
                '"key_findings" (array of strings), "recommendations" (array of strings).'
            ),
        }

        return (
            f"{base}\n\n"
            f"{type_instructions.get(report_type, type_instructions['general'])}\n\n"
            f"{format_instructions.get(output_format, format_instructions['markdown'])}"
        )

    @staticmethod
    def _ensure_json(content: str) -> str:
        """Try to extract valid JSON from the LLM output."""
        content = content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines)
        try:
            obj = json.loads(content)
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # Wrap raw text as JSON
            return json.dumps(
                {
                    "title": "Report",
                    "summary": content[:500],
                    "raw_content": content,
                },
                indent=2,
                ensure_ascii=False,
            )

    @staticmethod
    def _ensure_table(content: str) -> str:
        """Minimal post-processing for table output."""
        return content

    # ── Export helpers ────────────────────────────────────
    @staticmethod
    def export_csv(data: list[dict[str, Any]]) -> str:
        """Export list-of-dicts as CSV string."""
        if not data:
            return ""
        import csv
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return buf.getvalue()

    @staticmethod
    def export_json(data: Any) -> str:
        """Export data as formatted JSON string."""
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
