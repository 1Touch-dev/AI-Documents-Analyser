"""
Currency Service – detects monetary values in LLM response text and converts
them to the user-selected currency using real-time rates from Frankfurter.app.

No API key required. Rates are cached in Redis for 1 hour.

Usage
-----
    from services.currency_service import CurrencyService
    svc = CurrencyService()
    converted_text = await svc.convert_in_text(answer_text, "EUR")
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

# ── Currency symbols & codes ─────────────────────────────────
# Maps textual symbols to ISO 4217 codes
SYMBOL_TO_CODE: dict[str, str] = {
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "R$": "BRL",
    "BRL": "BRL",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
}

SUPPORTED_TARGETS = {"USD", "BRL", "EUR", "GBP"}

# Regex: matches patterns like "R$ 1.200.000,00" / "$1,200,000.00" / "€ 500K"
_MONEY_PATTERN = re.compile(
    r"(?P<symbol>R\$|US\$|\$|€|£|USD|BRL|EUR|GBP)"
    r"\s*"
    r"(?P<amount>[\d.,]+)"
    r"(?:\s*(?P<suffix>mil|milhões|bilhões|million|billion|thousand|M|MM|K|B|bn))?",
    re.IGNORECASE,
)

# Multipliers for suffix abbreviations
_SUFFIX_MULTIPLIERS: dict[str, float] = {
    "k": 1_000,
    "thousand": 1_000,
    "mil": 1_000,
    "m": 1_000_000,
    "mm": 1_000_000,
    "million": 1_000_000,
    "milhões": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
    "bilhões": 1_000_000_000,
}


def _parse_amount(amount_str: str, suffix: str | None) -> float:
    """
    Parse a string like "1.200.000" or "1,200,000" or "1.2" into a float.
    Handles both Brazilian (period=thousands, comma=decimal) and
    English (comma=thousands, period=decimal) number formats.
    """
    s = amount_str.strip()

    # Determine number format by analysing separators
    dot_idx = s.rfind(".")
    comma_idx = s.rfind(",")

    if dot_idx > comma_idx:
        # Likely English format: 1,200,000.50
        s = s.replace(",", "")
    elif comma_idx > dot_idx:
        # Likely Brazilian format: 1.200.000,50
        s = s.replace(".", "").replace(",", ".")
    # else: no separators

    try:
        value = float(s)
    except ValueError:
        return 0.0

    if suffix:
        multiplier = _SUFFIX_MULTIPLIERS.get(suffix.lower().strip(), 1.0)
        value *= multiplier

    return value


class CurrencyService:
    """
    Fetches exchange rates from Frankfurter.app and converts monetary values
    found inside LLM response text.
    """

    _FRANKFURTER_URL = "https://api.frankfurter.app/latest"
    _CACHE_KEY_PREFIX = "currency_rate:"

    def __init__(self) -> None:
        self._redis: Any | None = None
        self._http = httpx.AsyncClient(timeout=10.0)
        self._try_connect_redis()

    def _try_connect_redis(self) -> None:
        try:
            import redis as redis_lib
            client = redis_lib.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            self._redis = client
        except Exception as e:
            logger.warning("CurrencyService: Redis unavailable (%s). Rates won't be cached.", e)

    def _get_cached_rate(self, from_code: str, to_code: str) -> float | None:
        if not self._redis:
            return None
        try:
            raw = self._redis.get(f"{self._CACHE_KEY_PREFIX}{from_code}:{to_code}")
            return float(raw) if raw else None
        except Exception:
            return None

    def _set_cached_rate(self, from_code: str, to_code: str, rate: float) -> None:
        if not self._redis:
            return
        try:
            self._redis.setex(
                f"{self._CACHE_KEY_PREFIX}{from_code}:{to_code}",
                settings.currency_cache_ttl,
                str(rate),
            )
        except Exception:
            pass

    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Fetch the exchange rate from Frankfurter.app with Redis caching.
        Returns 1.0 if currencies are the same or if fetch fails.
        """
        from_code = from_currency.upper()
        to_code = to_currency.upper()

        if from_code == to_code:
            return 1.0

        # Check cache
        cached = self._get_cached_rate(from_code, to_code)
        if cached is not None:
            return cached

        try:
            resp = await self._http.get(
                self._FRANKFURTER_URL,
                params={"from": from_code, "to": to_code},
            )
            resp.raise_for_status()
            data = resp.json()
            rate: float = data["rates"][to_code]
            self._set_cached_rate(from_code, to_code, rate)
            return rate
        except Exception as e:
            logger.warning(
                "CurrencyService: Failed to fetch rate %s→%s (%s). Returning 1.0.", from_code, to_code, e
            )
            return 1.0

    async def convert_in_text(self, text: str, target_currency: str) -> str:
        """
        Find all monetary values in `text`, convert them to `target_currency`,
        and annotate inline.

        Example output:
          "Revenue was R$ 1.200.000"
          → "Revenue was R$ 1.200.000 (≈ USD 228,000)"
        """
        if target_currency.upper() not in SUPPORTED_TARGETS:
            logger.warning(
                "CurrencyService: Unsupported target currency '%s'. Skipping.", target_currency
            )
            return text

        matches = list(_MONEY_PATTERN.finditer(text))
        if not matches:
            return text

        # Pre-fetch all unique from→target rate pairs
        from_codes = {SYMBOL_TO_CODE.get(m.group("symbol").upper(), "USD") for m in matches}
        rates: dict[str, float] = {}
        for code in from_codes:
            rates[code] = await self.get_rate(code, target_currency.upper())

        # Build converted result (iterate in reverse to preserve string positions)
        result = text
        for match in reversed(matches):
            symbol = match.group("symbol")
            from_code = SYMBOL_TO_CODE.get(symbol.upper(), "USD")
            amount = _parse_amount(match.group("amount"), match.group("suffix"))

            if amount == 0.0:
                continue

            rate = rates.get(from_code, 1.0)
            converted = amount * rate

            # Format the converted value
            if converted >= 1_000_000:
                display = f"{converted / 1_000_000:.2f}M"
            elif converted >= 1_000:
                display = f"{converted / 1_000:.1f}K"
            else:
                display = f"{converted:,.2f}"

            annotation = f" (≈ {target_currency.upper()} {display})"

            # Only annotate if the currency isn't already the target
            if from_code != target_currency.upper():
                end = match.end()
                result = result[:end] + annotation + result[end:]

        return result

    async def close(self) -> None:
        await self._http.aclose()
