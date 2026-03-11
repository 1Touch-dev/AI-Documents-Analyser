"""
Document Parser – extracts text from various file formats.

Supported: PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DocumentParser:
    """Stateless document text extractor."""

    SUPPORTED_TYPES = {"pdf", "docx", "pptx", "xlsx", "csv", "txt", "json"}

    # ── Public API ───────────────────────────────────────
    def parse(self, file_bytes: bytes, file_type: str) -> str:
        """
        Extract plain text from raw bytes of a document.

        Parameters
        ----------
        file_bytes : bytes
            Raw file content.
        file_type : str
            Lowercase extension (e.g. ``"pdf"``).

        Returns
        -------
        str
            Extracted text.
        """
        file_type = file_type.lower().lstrip(".")
        if file_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        handler = getattr(self, f"_parse_{file_type}")
        text: str = handler(file_bytes)
        logger.info("Parsed %s document – %d chars extracted", file_type, len(text))
        return text

    def extract_metadata(self, file_bytes: bytes, file_type: str) -> dict[str, Any]:
        """Extract basic metadata from a document."""
        file_type = file_type.lower().lstrip(".")
        return {
            "file_type": file_type,
            "size_bytes": len(file_bytes),
            "char_count": len(self.parse(file_bytes, file_type)),
        }

    # ── Private parsers ──────────────────────────────────
    @staticmethod
    def _parse_pdf(data: bytes) -> str:
        import fitz  # PyMuPDF

        text_parts: list[str] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n".join(text_parts)

    @staticmethod
    def _parse_docx(data: bytes) -> str:
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(data))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

    @staticmethod
    def _parse_pptx(data: bytes) -> str:
        from pptx import Presentation

        prs = Presentation(io.BytesIO(data))
        text_parts: list[str] = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text_parts.append(shape.text_frame.text)
        return "\n".join(text_parts)

    @staticmethod
    def _parse_xlsx(data: bytes) -> str:
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        text_parts: list[str] = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                text_parts.append("\t".join(cells))
        return "\n".join(text_parts)

    @staticmethod
    def _parse_csv(data: bytes) -> str:
        text = data.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return "\n".join("\t".join(row) for row in reader)

    @staticmethod
    def _parse_txt(data: bytes) -> str:
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _parse_json(data: bytes) -> str:
        obj = json.loads(data.decode("utf-8", errors="replace"))
        return json.dumps(obj, indent=2, ensure_ascii=False)
