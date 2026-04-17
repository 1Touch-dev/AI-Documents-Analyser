"""
Translation Service – translates document chunks using the primary local model
(Gemma 4 E2B via Ollama) before they are passed to the RAG pipeline.

This keeps translation fast and free (no external API calls).
Redis caching avoids re-translating identical chunks.

Usage
-----
    from services.translation_service import TranslationService
    svc = TranslationService(llm_router)
    translated_chunks = await svc.translate_chunks(chunks, target_language="English")
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from config.settings import settings

if TYPE_CHECKING:
    from backend.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# Translation prompt template
_TRANSLATE_PROMPT = (
    "You are a professional translator. Translate the following text to {target_language}. "
    "Preserve all numbers, proper nouns, currency values, and technical terms exactly as they appear. "
    "Output ONLY the translated text — no explanations, no preamble, no quotes.\n\n"
    "Text to translate:\n{text}"
)


class TranslationService:
    """
    Translates a list of text chunks using the local Gemma model.

    Parameters
    ----------
    llm_router : LLMRouter
        The shared LLM router instance.
    """

    def __init__(self, llm_router: "LLMRouter") -> None:
        self._llm = llm_router
        self._redis: object | None = None
        self._try_connect_redis()

    def _try_connect_redis(self) -> None:
        """Attempt to connect to Redis for caching; silently skip if unavailable."""
        try:
            import redis as redis_lib
            client = redis_lib.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            self._redis = client
            logger.info("TranslationService: Redis cache connected.")
        except Exception as e:
            logger.warning(
                "TranslationService: Redis unavailable (%s). Translations won't be cached.", e
            )

    def _cache_key(self, text: str, target_language: str) -> str:
        """Generate a stable Redis key from text content + target language."""
        digest = hashlib.sha256(f"{target_language}:{text}".encode()).hexdigest()[:16]
        return f"translation:{digest}"

    def _get_cached(self, text: str, target_language: str) -> str | None:
        if not self._redis:
            return None
        try:
            return self._redis.get(self._cache_key(text, target_language))  # type: ignore[union-attr]
        except Exception:
            return None

    def _set_cached(self, text: str, target_language: str, translated: str) -> None:
        if not self._redis:
            return
        try:
            self._redis.setex(  # type: ignore[union-attr]
                self._cache_key(text, target_language),
                settings.cache_ttl_seconds,
                translated,
            )
        except Exception:
            pass

    async def translate_chunk(self, text: str, target_language: str = "English") -> str:
        """
        Translate a single chunk. Returns the original text if translation fails.
        """
        if not text.strip():
            return text

        # Cache hit?
        cached = self._get_cached(text, target_language)
        if cached:
            return cached

        prompt = _TRANSLATE_PROMPT.format(
            target_language=target_language,
            text=text,
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            # Always use the local Gemma model for translation (force_local=True)
            model = self._llm.resolve_model("auto", force_local=True)
            translated, _ = await self._llm.generate_with_fallback(
                preferred_model=model,
                messages=messages,
                temperature=0.1,   # Low temp for faithful translation
                max_tokens=1500,
            )
            translated = translated.strip()
            if translated:
                self._set_cached(text, target_language, translated)
                return translated
        except Exception as e:
            logger.warning(
                "TranslationService.translate_chunk failed (%s). Returning original.", e
            )

        return text  # Graceful fallback: return original text

    async def translate_chunks(
        self,
        chunks: list[str],
        target_language: str | None = None,
    ) -> list[str]:
        """
        Translate a list of chunks in parallel (batch of individual awaits).

        Parameters
        ----------
        chunks : list[str]
            Raw text chunks from vector store retrieval.
        target_language : str, optional
            Language to translate to. Defaults to settings.translate_target_language.

        Returns
        -------
        list[str]
            Translated chunks (same length as input).
        """
        lang = target_language or settings.translate_target_language
        import asyncio
        results = await asyncio.gather(
            *[self.translate_chunk(chunk, lang) for chunk in chunks],
            return_exceptions=False,
        )
        return list(results)
