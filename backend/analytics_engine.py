"""
Analytics Engine – computes document statistics, topic extraction,
similarity data, and aggregations for Tableau-level dashboards.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import Document

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Compute analytics over ingested documents."""

    # ── Overview Stats ────────────────────────────────────
    @staticmethod
    def overview(db: Session) -> dict[str, Any]:
        """Aggregated overview for the dashboard."""
        docs = db.query(Document).all()
        if not docs:
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "total_size_bytes": 0,
                "by_status": {},
                "by_category": {},
                "by_file_type": {},
                "by_uploader": {},
                "avg_chunks_per_doc": 0,
                "avg_file_size": 0,
            }

        total_chunks = sum(d.chunk_count or 0 for d in docs)
        total_size = sum(d.file_size or 0 for d in docs)

        status_counts = Counter(d.status for d in docs)
        category_counts = Counter(d.category for d in docs)
        type_counts = Counter(d.file_type for d in docs)
        uploader_counts = Counter(d.uploaded_by for d in docs)

        return {
            "total_documents": len(docs),
            "total_chunks": total_chunks,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_status": dict(status_counts),
            "by_category": dict(category_counts),
            "by_file_type": dict(type_counts),
            "by_uploader": dict(uploader_counts),
            "avg_chunks_per_doc": round(total_chunks / len(docs), 1) if docs else 0,
            "avg_file_size_kb": round(total_size / len(docs) / 1024, 1) if docs else 0,
        }

    # ── Content Statistics ────────────────────────────────
    @staticmethod
    def content_stats(db: Session, vector_store=None) -> dict[str, Any]:
        """Word counts, reading time, word frequency from stored documents."""
        docs = db.query(Document).filter(Document.status == "ready").all()

        doc_stats = []
        all_words: list[str] = []

        for d in docs:
            chunk_count = d.chunk_count or 0
            # Estimate word count from chunks (~200 words per chunk)
            estimated_words = chunk_count * 200
            reading_time_min = round(estimated_words / 250, 1)  # 250 wpm

            doc_stats.append({
                "id": str(d.id),
                "title": d.title,
                "category": d.category,
                "file_type": d.file_type,
                "chunk_count": chunk_count,
                "estimated_words": estimated_words,
                "reading_time_min": reading_time_min,
                "file_size_kb": round((d.file_size or 0) / 1024, 1),
            })

        # Get word frequencies from vector store if available
        word_freq = {}
        if vector_store:
            try:
                # Sample some chunks for word frequency analysis
                all_chunks = vector_store.get_all_documents(limit=200)
                for chunk in all_chunks:
                    text = chunk.get("document", "")
                    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
                    all_words.extend(words)

                # Filter common stop words
                stop_words = {
                    "the", "and", "for", "are", "but", "not", "you", "all",
                    "can", "had", "her", "was", "one", "our", "out", "has",
                    "have", "been", "were", "will", "with", "this", "that",
                    "from", "they", "which", "their", "would", "there",
                    "about", "each", "make", "like", "than", "them", "then",
                    "into", "over", "such", "also", "more", "some", "very",
                    "when", "what", "your", "how", "its", "may", "these",
                    "other", "could", "just", "only", "any", "most",
                }
                filtered = [w for w in all_words if w not in stop_words]
                word_freq = dict(Counter(filtered).most_common(100))
            except Exception as e:
                logger.warning("Word frequency analysis failed: %s", e)

        return {
            "documents": doc_stats,
            "word_frequencies": word_freq,
            "total_estimated_words": sum(d["estimated_words"] for d in doc_stats),
            "total_reading_time_min": round(sum(d["reading_time_min"] for d in doc_stats), 1),
        }

    # ── Storage Analytics ─────────────────────────────────
    @staticmethod
    def storage_stats(db: Session) -> dict[str, Any]:
        """File size distribution, storage by type, growth over time."""
        docs = db.query(Document).order_by(Document.timestamp).all()

        size_by_type: dict[str, int] = {}
        size_by_category: dict[str, int] = {}
        daily_uploads: dict[str, dict] = {}

        for d in docs:
            ftype = d.file_type or "unknown"
            cat = d.category or "uncategorized"
            fsize = d.file_size or 0

            size_by_type[ftype] = size_by_type.get(ftype, 0) + fsize
            size_by_category[cat] = size_by_category.get(cat, 0) + fsize

            if d.timestamp:
                day = d.timestamp.strftime("%Y-%m-%d")
                if day not in daily_uploads:
                    daily_uploads[day] = {"count": 0, "size": 0, "cumulative_count": 0, "cumulative_size": 0}
                daily_uploads[day]["count"] += 1
                daily_uploads[day]["size"] += fsize

        # Calculate cumulative values
        running_count = 0
        running_size = 0
        for day in sorted(daily_uploads.keys()):
            running_count += daily_uploads[day]["count"]
            running_size += daily_uploads[day]["size"]
            daily_uploads[day]["cumulative_count"] = running_count
            daily_uploads[day]["cumulative_size"] = running_size

        # Size distribution buckets
        size_buckets = {"<10KB": 0, "10-100KB": 0, "100KB-1MB": 0, "1-10MB": 0, "10-100MB": 0, ">100MB": 0}
        for d in docs:
            s = d.file_size or 0
            if s < 10240:
                size_buckets["<10KB"] += 1
            elif s < 102400:
                size_buckets["10-100KB"] += 1
            elif s < 1048576:
                size_buckets["100KB-1MB"] += 1
            elif s < 10485760:
                size_buckets["1-10MB"] += 1
            elif s < 104857600:
                size_buckets["10-100MB"] += 1
            else:
                size_buckets[">100MB"] += 1

        return {
            "size_by_type": {k: round(v / 1024, 1) for k, v in size_by_type.items()},  # KB
            "size_by_category": {k: round(v / 1024, 1) for k, v in size_by_category.items()},  # KB
            "daily_uploads": daily_uploads,
            "size_distribution": size_buckets,
        }

    # ── File Hash for Duplicate Detection ─────────────────
    @staticmethod
    def compute_hash(content: bytes) -> str:
        """SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def check_duplicate(db: Session, file_hash: str) -> dict | None:
        """Check if a file with this hash already exists (excluding failed attempts)."""
        existing = db.query(Document).filter(
            Document.content_hash == file_hash,
            Document.status != "failed"
        ).first()
        if existing:
            return {
                "is_duplicate": True,
                "existing_id": str(existing.id),
                "existing_title": existing.title,
            }
        return None

    # ══════════════════════════════════════════════════════
    #  CONTENT-DRIVEN ANALYTICS (Phase 8)
    # ══════════════════════════════════════════════════════

    @staticmethod
    def content_insights(db: Session, vector_store=None) -> dict[str, Any]:
        """
        Extract actionable insights FROM document content:
        topics, entities, financial data, relationships, per-doc summaries.
        """
        docs = db.query(Document).filter(Document.status == "ready").all()
        doc_map = {str(d.id): d for d in docs}

        # Gather all chunks grouped by document
        chunks_by_doc: dict[str, list[str]] = {}
        all_chunks: list[dict] = []

        if vector_store:
            try:
                raw = vector_store.get_all_documents(limit=2000)
                for c in raw:
                    doc_id = c.get("metadata", {}).get("doc_id", "unknown")
                    text = c.get("document", "")
                    if text:
                        chunks_by_doc.setdefault(doc_id, []).append(text)
                        all_chunks.append(c)
            except Exception as e:
                logger.warning("Failed to fetch chunks for content analytics: %s", e)

        # Merge all text for global analysis
        all_text_parts = []
        for texts in chunks_by_doc.values():
            all_text_parts.extend(texts)
        full_corpus = "\n".join(all_text_parts)

        # 1. Topic extraction
        topics = AnalyticsEngine._extract_topics(all_text_parts)

        # 2. Entity extraction
        entities = AnalyticsEngine._extract_entities(full_corpus)

        # 3. Financial data detection
        financials = AnalyticsEngine._extract_financial_items(full_corpus)

        # 4. Per-document insights
        doc_insights = AnalyticsEngine._build_doc_summaries(chunks_by_doc, doc_map)

        # 5. Content coverage matrix (topics × documents)
        coverage = AnalyticsEngine._build_coverage_matrix(chunks_by_doc, doc_map, topics)

        # 6. Cross-document similarity (simple Jaccard on key terms)
        similarity = AnalyticsEngine._compute_similarity_matrix(chunks_by_doc, doc_map)

        return {
            "topics": topics,
            "entities": entities,
            "financials": financials,
            "doc_insights": doc_insights,
            "coverage_matrix": coverage,
            "similarity_matrix": similarity,
            "summary": {
                "total_topics": len(topics),
                "total_entities": sum(len(v) for v in entities.values()),
                "total_financial_items": len(financials),
                "docs_analyzed": len(chunks_by_doc),
                "chunks_analyzed": len(all_chunks),
            },
        }

    # ── Topic Extraction ─────────────────────────────────
    @staticmethod
    def _extract_topics(text_parts: list[str], max_topics: int = 20) -> list[dict]:
        """Extract dominant topics using n-gram frequency analysis."""
        from collections import Counter
        import re

        stop_words = {
            # English
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "had", "her", "was", "one", "our", "out", "has", "have", "been",
            "were", "will", "with", "this", "that", "from", "they", "which",
            "their", "would", "there", "about", "each", "make", "like",
            "than", "them", "then", "into", "over", "such", "also", "more",
            "some", "very", "when", "what", "your", "how", "its", "may",
            "these", "other", "could", "just", "only", "any", "most",
            "none", "does", "did", "should", "shall", "must", "being",
            "who", "whom", "where", "here", "both", "few", "those",
            "same", "own", "too", "than", "nor", "yet", "get", "got",
            "per", "via", "use", "used", "using", "page", "see", "new",
            "old", "well", "still", "even", "back", "come", "take",
            "know", "long", "much", "many", "way", "part", "need",
            "last", "first", "next", "number", "data", "time", "year",
            # Portuguese
            "para", "com", "que", "uma", "por", "dos", "das", "nos", "nas",
            "entre", "mais", "como", "ser", "ter", "seus", "sua", "seu",
            "isso", "essa", "esse", "esta", "este", "cada", "sem", "sob",
            "não", "sim", "nos", "ela", "ele", "são", "foi", "tem",
            "onde", "qual", "quais", "muito", "pode", "após", "até",
            "sobre", "quando", "desde", "apenas", "caso", "ainda",
            "assim", "toda", "todo", "todos", "todas", "outro", "outra",
            "outros", "outras", "novo", "nova", "maior", "menor",
            "pela", "pelo", "pelas", "pelos", "numa", "nessa", "nesse",
            "conforme", "também", "bem", "dia", "mês", "ano",
        }

        # Collect bigrams and meaningful unigrams
        bigram_counter: Counter = Counter()
        unigram_counter: Counter = Counter()

        for text in text_parts:
            words = re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text.lower())
            filtered = [w for w in words if w not in stop_words]

            for w in filtered:
                unigram_counter[w] += 1

            for i in range(len(filtered) - 1):
                # Skip bigrams where both words are the same
                if filtered[i] == filtered[i+1]:
                    continue
                bigram = f"{filtered[i]} {filtered[i+1]}"
                bigram_counter[bigram] += 1

        # Merge: prefer bigrams that appear frequently
        topics = []
        seen_words = set()
        for phrase, count in bigram_counter.most_common(max_topics * 2):
            if count < 3:
                continue
            words_in_phrase = set(phrase.split())
            if not words_in_phrase & seen_words:
                topics.append({"topic": phrase, "frequency": count, "type": "bigram"})
                seen_words |= words_in_phrase
            if len(topics) >= max_topics // 2:
                break

        # Fill remaining with top unigrams
        for word, count in unigram_counter.most_common(max_topics * 3):
            if word in seen_words or count < 5:
                continue
            topics.append({"topic": word, "frequency": count, "type": "unigram"})
            seen_words.add(word)
            if len(topics) >= max_topics:
                break

        topics.sort(key=lambda t: t["frequency"], reverse=True)
        return topics[:max_topics]

    # ── Entity Extraction ────────────────────────────────
    @staticmethod
    def _extract_entities(text: str) -> dict[str, list[dict]]:
        """Extract named entities using pattern matching."""
        import re

        entities: dict[str, list[dict]] = {
            "monetary": [],
            "percentages": [],
            "dates": [],
            "emails": [],
            "urls": [],
            "organizations": [],
        }

        # Monetary values (R$, $, €, £, etc.)
        money_patterns = re.findall(
            r'(?:R\$|US\$|\$|€|£)\s*[\d.,]+(?:\s*(?:mil|milhões|bilhões|million|billion|thousand|MM|M|K|B))?',
            text, re.IGNORECASE
        )
        money_counter = Counter(money_patterns)
        for val, count in money_counter.most_common(30):
            entities["monetary"].append({"value": val.strip(), "occurrences": count})

        # Percentages
        pct_patterns = re.findall(r'[\d.,]+\s*%', text)
        pct_counter = Counter(pct_patterns)
        for val, count in pct_counter.most_common(20):
            entities["percentages"].append({"value": val.strip(), "occurrences": count})

        # Dates (various formats)
        date_patterns = re.findall(
            r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4}\b',
            text, re.IGNORECASE
        )
        date_counter = Counter(date_patterns)
        for val, count in date_counter.most_common(20):
            entities["dates"].append({"value": val.strip(), "occurrences": count})

        # Emails
        email_patterns = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for e in set(email_patterns):
            entities["emails"].append({"value": e, "occurrences": email_patterns.count(e)})

        # URLs
        url_patterns = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+', text)
        url_counter = Counter(url_patterns)
        for val, count in url_counter.most_common(10):
            entities["urls"].append({"value": val.strip(), "occurrences": count})

        # Organization-like patterns (Title Case multi-word)
        org_patterns = re.findall(r'\b(?:[A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:de|do|da|dos|das|e|&)\s+)?){2,4}(?:S\.?A\.?|Ltda\.?|Inc\.?|LLC|Corp\.?|Ltd\.?|Group|Grupo|Futebol|Club[e]?)?\b', text)
        org_counter = Counter(org_patterns)
        for val, count in org_counter.most_common(20):
            clean = val.strip()
            if len(clean) > 5 and count >= 2:
                entities["organizations"].append({"value": clean, "occurrences": count})

        return entities

    # ── Financial Data Detection ──────────────────────────
    @staticmethod
    def _extract_financial_items(text: str) -> list[dict]:
        """Detect structured financial data: budget lines, revenue, expenses."""
        import re

        items = []
        financial_keywords = [
            "receita", "despesa", "custo", "lucro", "prejuízo", "saldo",
            "revenue", "expense", "cost", "profit", "loss", "balance",
            "budget", "forecast", "orçamento", "previsão", "investimento",
            "faturamento", "margem", "ebitda", "fluxo de caixa", "cash flow",
            "patrocínio", "sponsorship", "bonificação", "salário", "folha",
        ]

        for keyword in financial_keywords:
            pattern = re.compile(
                rf'(?:^|[.\n])([^\n]{{0,80}}{keyword}[^\n]{{0,80}})',
                re.IGNORECASE | re.MULTILINE
            )
            matches = pattern.findall(text)
            for match in matches[:3]:  # cap at 3 per keyword
                clean = match.strip()
                if len(clean) > 15:
                    # Try to extract a number from the context
                    numbers = re.findall(r'[\d.,]+(?:\s*(?:mil|milhões|M|K|%))?', clean)
                    items.append({
                        "context": clean[:150],
                        "keyword": keyword,
                        "values_found": numbers[:5],
                    })

        # Deduplicate by context similarity
        seen = set()
        unique_items = []
        for item in items:
            key = item["context"][:50]
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        return unique_items[:50]

    # ── Per-Document Summaries ────────────────────────────
    @staticmethod
    def _build_doc_summaries(
        chunks_by_doc: dict[str, list[str]], doc_map: dict
    ) -> list[dict]:
        """Build actionable per-document insights: bigram themes + financial values."""
        import re
        import html as html_mod

        stop_words = {
            # English
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "had", "her", "was", "one", "our", "out", "has", "have", "been",
            "were", "will", "with", "this", "that", "from", "they", "which",
            "their", "would", "there", "about", "each", "make", "like",
            "than", "them", "then", "into", "over", "such", "also", "more",
            "some", "very", "when", "what", "your", "how", "its", "may",
            "these", "other", "could", "just", "only", "any", "most",
            "none", "does", "did", "page", "see", "data", "time",
            # Portuguese
            "para", "com", "que", "uma", "por", "dos", "das", "nos", "nas",
            "entre", "mais", "como", "ser", "ter", "seus", "sua", "seu",
            "isso", "essa", "esse", "esta", "este", "cada", "sem", "sob",
            "não", "sim", "ela", "ele", "são", "foi", "tem",
            "onde", "qual", "quais", "muito", "pode", "após", "até",
            "sobre", "quando", "desde", "apenas", "caso", "ainda",
            "assim", "toda", "todo", "todos", "todas", "outro", "outra",
            "pela", "pelo", "pelas", "pelos", "conforme", "também",
        }

        results = []
        for doc_id, chunks in chunks_by_doc.items():
            doc = doc_map.get(doc_id)
            if not doc:
                continue

            full_text = " ".join(chunks)
            words = re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', full_text.lower())
            filtered = [w for w in words if w not in stop_words]

            # Generate bigram phrases (more meaningful than single words)
            bigram_counter: Counter = Counter()
            unigram_counter: Counter = Counter()
            for w in filtered:
                unigram_counter[w] += 1
            for i in range(len(filtered) - 1):
                if filtered[i] != filtered[i + 1]:
                    bigram_counter[f"{filtered[i]} {filtered[i+1]}"] += 1

            # Prefer bigrams, fall back to unigrams
            key_phrases = []
            seen = set()
            for phrase, cnt in bigram_counter.most_common(20):
                if cnt < 2:
                    break
                w1, w2 = phrase.split()
                if w1 not in seen and w2 not in seen:
                    key_phrases.append(phrase)
                    seen.update([w1, w2])
                if len(key_phrases) >= 5:
                    break
            # Fill with top unigrams
            for word, cnt in unigram_counter.most_common(30):
                if word in seen or cnt < 3:
                    continue
                key_phrases.append(word)
                seen.add(word)
                if len(key_phrases) >= 10:
                    break

            # Extract only meaningful monetary/percentage values
            monetary_vals = re.findall(
                r'(?:R\$|US\$|\$|€|£)\s*[\d.,]+(?:\s*(?:mil|milhões|M|K|B))?',
                full_text, re.IGNORECASE
            )
            pct_vals = re.findall(r'[\d.,]+\s*%', full_text)
            notable = list(set(monetary_vals))[:6] + list(set(pct_vals))[:4]

            # Build a clean text preview (strip extra whitespace, escape HTML)
            preview_text = " ".join(full_text[:400].split())
            preview_text = html_mod.escape(preview_text)

            results.append({
                "doc_id": doc_id,
                "title": doc.title,
                "file_type": doc.file_type,
                "category": doc.category,
                "chunk_count": doc.chunk_count or len(chunks),
                "key_phrases": key_phrases,
                "notable_values": notable,
                "text_preview": preview_text,
            })

        return results

    # ── Content Coverage Matrix ──────────────────────────
    @staticmethod
    def _build_coverage_matrix(
        chunks_by_doc: dict[str, list[str]],
        doc_map: dict,
        topics: list[dict],
    ) -> dict:
        """Build topics × documents coverage matrix."""
        import re

        topic_labels = [t["topic"] for t in topics[:15]]
        doc_ids = [did for did in chunks_by_doc if did in doc_map]

        matrix = []
        doc_titles = []
        for doc_id in doc_ids:
            doc = doc_map.get(doc_id)
            if not doc:
                continue
            doc_titles.append(doc.title[:30])
            full_text = " ".join(chunks_by_doc[doc_id]).lower()
            row = []
            for topic in topic_labels:
                count = len(re.findall(re.escape(topic), full_text))
                row.append(count)
            matrix.append(row)

        return {
            "topics": topic_labels,
            "documents": doc_titles,
            "matrix": matrix,
        }

    # ── Cross-Document Similarity ────────────────────────
    @staticmethod
    def _compute_similarity_matrix(
        chunks_by_doc: dict[str, list[str]], doc_map: dict
    ) -> dict:
        """Jaccard similarity between documents based on key terms."""
        import re

        stop_words = {
            "the", "and", "for", "are", "but", "not", "you", "all",
            "can", "had", "her", "was", "one", "our", "has", "have",
            "been", "were", "will", "with", "this", "that", "from",
        }

        doc_terms: dict[str, set] = {}
        doc_titles: list[str] = []
        doc_ids_ordered: list[str] = []

        for doc_id, chunks in chunks_by_doc.items():
            doc = doc_map.get(doc_id)
            if not doc:
                continue
            full_text = " ".join(chunks).lower()
            words = set(re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', full_text))
            words -= stop_words
            doc_terms[doc_id] = words
            doc_titles.append(doc.title[:30])
            doc_ids_ordered.append(doc_id)

        n = len(doc_ids_ordered)
        matrix = []
        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    row.append(1.0)
                else:
                    set_a = doc_terms[doc_ids_ordered[i]]
                    set_b = doc_terms[doc_ids_ordered[j]]
                    intersection = len(set_a & set_b)
                    union = len(set_a | set_b)
                    row.append(round(intersection / union, 3) if union > 0 else 0)
            matrix.append(row)

        return {
            "documents": doc_titles,
            "matrix": matrix,
        }
