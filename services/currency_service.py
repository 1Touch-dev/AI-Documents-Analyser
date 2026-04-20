"""
Currency conversion helpers for response post-processing.

Primary API : fawazahmed0 currency-api (fully free, open-source, 150+ currencies)
              https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json
Fallback API: open.er-api.com (free, no key required)
Static fallback: USD cross-rate table (used only when both APIs are unreachable)
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

# ── Rate cache ────────────────────────────────────────────────────────────────
_rate_cache: dict[str, tuple[float, float]] = {}
_CACHE_TTL = 3600  # 1 hour

# Static fallback cross-rates via USD (used only if all live APIs fail)
_FALLBACK_FROM_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92, "GBP": 0.79, "CHF": 0.90,
    "NOK": 10.55, "SEK": 10.42, "DKK": 6.89,
    "PLN": 3.98, "CZK": 22.8, "HUF": 357.0, "RON": 4.57, "TRY": 32.5,
    "RUB": 90.0, "UAH": 38.5,
    "BRL": 5.50, "ARS": 870.0, "CLP": 940.0, "COP": 3950.0, "PEN": 3.72,
    "MXN": 17.5, "CAD": 1.36, "AUD": 1.53, "NZD": 1.63,
    "JPY": 150.0, "CNY": 7.24, "INR": 83.0, "KRW": 1340.0,
    "SGD": 1.34, "HKD": 7.82, "TWD": 31.8, "THB": 35.2,
    "IDR": 15800.0, "MYR": 4.72, "PHP": 56.5, "VND": 24500.0,
    "AED": 3.67, "SAR": 3.75, "QAR": 3.64, "ILS": 3.70,
    "EGP": 30.9, "ZAR": 18.7, "NGN": 1560.0, "KES": 129.0,
    "PKR": 278.0, "BDT": 110.0,
}


# ── Live API helpers ──────────────────────────────────────────────────────────

def _try_fawazahmed(fc: str, tc: str) -> Optional[float]:
    """fawazahmed0 currency-api — free, open-source, 150+ currencies, no key."""
    base = fc.lower()
    target = tc.lower()
    url = (
        f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest"
        f"/v1/currencies/{base}.json"
    )
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        return float(data[base][target])
    except Exception as exc:
        logger.debug("fawazahmed0 API failed (%s→%s): %s", fc, tc, exc)
        return None


def _try_open_er_api(fc: str, tc: str) -> Optional[float]:
    """open.er-api.com — free, no key required."""
    url = f"https://open.er-api.com/v6/latest/{fc}"
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        return float(data["rates"][tc])
    except Exception as exc:
        logger.debug("open.er-api.com failed (%s→%s): %s", fc, tc, exc)
        return None


def fetch_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Return the live exchange rate *from_currency* → *to_currency*.

    Tries fawazahmed0 first (free open-source), then open.er-api.com,
    then a static USD cross-rate table.  Results cached for 1 hour.
    """
    fc = from_currency.upper()
    tc = to_currency.upper()
    if fc == tc:
        return 1.0

    cache_key = f"{fc}_{tc}"
    now = time.monotonic()
    cached = _rate_cache.get(cache_key)
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    rate = _try_fawazahmed(fc, tc)
    if rate is None:
        rate = _try_open_er_api(fc, tc)
    if rate is None:
        usd_fc = _FALLBACK_FROM_USD.get(fc)
        usd_tc = _FALLBACK_FROM_USD.get(tc)
        if usd_fc and usd_tc and usd_fc != 0:
            rate = usd_tc / usd_fc
        else:
            rate = 1.0
        logger.warning("Both live APIs failed (%s→%s) — using static fallback.", fc, tc)

    _rate_cache[cache_key] = (rate, now)
    logger.debug("Rate %s→%s: %s", fc, tc, rate)
    return rate


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert *amount* from *from_currency* to *to_currency* using live rates."""
    if from_currency.upper() == to_currency.upper():
        return amount
    return amount * fetch_exchange_rate(from_currency, to_currency)


# ── CurrencyService ───────────────────────────────────────────────────────────

class CurrencyService:
    """Detect and convert currency amounts in free-form text (ANY → ANY)."""

    # All currencies accepted as target_currency in the query API.
    SUPPORTED_CURRENCIES: set[str] = {
        # Americas
        "BRL", "USD", "CAD", "MXN", "ARS", "CLP", "COP", "PEN",
        # Europe
        "EUR", "GBP", "CHF", "NOK", "SEK", "DKK",
        "PLN", "CZK", "HUF", "RON", "TRY", "RUB", "UAH",
        # Asia-Pacific
        "JPY", "CNY", "INR", "KRW", "SGD", "HKD", "TWD",
        "THB", "IDR", "MYR", "PHP", "VND", "AUD", "NZD",
        # Middle East / Africa
        "AED", "SAR", "QAR", "ILS", "EGP", "ZAR", "NGN", "KES",
        # South Asia
        "PKR", "BDT",
    }

    # Output symbol/prefix per currency code.
    SYMBOLS: dict[str, str] = {
        "BRL": "R$",  "USD": "$",   "EUR": "€",   "GBP": "£",
        "JPY": "¥",   "CNY": "¥",   "INR": "₹",   "KRW": "₩",
        "AUD": "A$",  "CAD": "C$",  "NZD": "NZ$", "SGD": "S$",
        "HKD": "HK$", "TWD": "NT$", "MXN": "MX$",
        "CHF": "CHF ", "NOK": "kr ", "SEK": "kr ", "DKK": "kr ",
        "PLN": "zł ", "CZK": "Kč ", "HUF": "Ft ", "RON": "lei ",
        "TRY": "₺",   "RUB": "₽",   "UAH": "₴",
        "ARS": "ARS ","CLP": "CLP ","COP": "COP ","PEN": "S/ ",
        "THB": "฿",   "IDR": "Rp ", "MYR": "RM ", "PHP": "₱",
        "VND": "₫",   "AED": "AED ","SAR": "SAR ","QAR": "QAR ",
        "ILS": "₪",   "EGP": "E£ ", "ZAR": "R ",  "NGN": "₦",
        "KES": "KSh ","PKR": "₨ ",  "BDT": "৳ ",
    }

    # Ordered symbol → ISO code (longer prefixes first).
    _SYMBOL_MAP: list[tuple[str, str]] = [
        ("R$",  "BRL"), ("A$",  "AUD"), ("C$",  "CAD"),
        ("NZ$", "NZD"), ("S$",  "SGD"), ("HK$", "HKD"),
        ("NT$", "TWD"), ("MX$", "MXN"),
        ("$",   "USD"), ("€",   "EUR"), ("£",   "GBP"),
        ("₹",   "INR"), ("¥",   "JPY"), ("₩",   "KRW"),
        ("₺",   "TRY"), ("₽",   "RUB"), ("₴",   "UAH"),
        ("฿",   "THB"), ("₱",   "PHP"), ("₦",   "NGN"),
        ("₪",   "ILS"), ("₫",   "VND"),
    ]

    # ISO codes matched in "100 USD" style patterns.
    _ISO_CODES: tuple[str, ...] = (
        "USD", "EUR", "GBP", "BRL", "INR", "JPY", "CNY", "KRW",
        "AUD", "CAD", "CHF", "NZD", "SGD", "HKD", "TWD", "MXN",
        "NOK", "SEK", "DKK", "PLN", "CZK", "HUF", "RON", "TRY",
        "RUB", "UAH", "ARS", "CLP", "COP", "PEN",
        "THB", "IDR", "MYR", "PHP", "VND",
        "AED", "SAR", "QAR", "ILS", "EGP", "ZAR", "NGN", "KES",
        "PKR", "BDT",
    )

    # Kept for backward-compat.
    RATES_FROM_BRL = {"BRL": 1.0, "USD": 0.18, "EUR": 0.16}

    # ── Compiled patterns ────────────────────────────────────────────────────

    _BRL_PATTERN = re.compile(
        r"R\$\s*(?P<value>\d[\d\.,]*)"
        r"(?:\s*(?P<suffix>milh(?:ao|oes|ão|ões)?|mil|mi|MM|[MK]))?",
        re.IGNORECASE,
    )

    _SYMBOL_PATTERN = re.compile(
        r"(?P<symbol>"
        r"R\$|A\$|C\$|NZ\$|S\$|HK\$|NT\$|MX\$"
        r"|\$|€|£|₹|¥|₩|₺|₽|₴|฿|₱|₦|₪|₫"
        r")\s*(?P<value>\d[\d\.,]*)"
    )

    _ISO_PATTERN = re.compile(
        r"(?P<value>\d[\d\.,]*)\s+"
        r"(?P<code>" + "|".join(_ISO_CODES) + r")\b",
        re.IGNORECASE,
    )

    # ── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def convert_text(cls, text: str, target_currency: str) -> str:
        target = (target_currency or "BRL").upper()
        if not text:
            return text

        replacements: list[tuple[int, int, str]] = []

        # Pass 1: R$ BRL with multipliers
        if target != "BRL":
            for m in cls._BRL_PATTERN.finditer(text):
                try:
                    amount = cls._parse_number(m.group("value"))
                    amount *= cls._parse_multiplier(m.group("suffix") or "")
                    converted = convert_currency(amount, "BRL", target)
                    replacements.append((m.start(), m.end(), cls._format_value(converted, target)))
                except Exception as exc:
                    logger.debug("BRL match skip: %s", exc)

        # Pass 2: symbol-prefix ($, €, £, ₹, ¥, …)
        for m in cls._SYMBOL_PATTERN.finditer(text):
            if cls._overlaps(m.start(), m.end(), replacements):
                continue
            source = cls._symbol_to_code(m.group("symbol"))
            if source is None or source == target:
                continue
            try:
                amount = cls._parse_number(m.group("value"))
                converted = convert_currency(amount, source, target)
                replacements.append((m.start(), m.end(), cls._format_value(converted, target)))
            except Exception as exc:
                logger.debug("Symbol match skip: %s", exc)

        # Pass 3: ISO-code suffix ("100 USD", "200.50 EUR")
        for m in cls._ISO_PATTERN.finditer(text):
            if cls._overlaps(m.start(), m.end(), replacements):
                continue
            source = m.group("code").upper()
            if source == target:
                continue
            try:
                amount = cls._parse_number(m.group("value"))
                converted = convert_currency(amount, source, target)
                replacements.append((m.start(), m.end(), cls._format_value(converted, target)))
            except Exception as exc:
                logger.debug("ISO match skip: %s", exc)

        if not replacements:
            return text

        replacements.sort(key=lambda r: r[0], reverse=True)
        result = text
        for start, end, replacement in replacements:
            result = result[:start] + replacement + result[end:]
        return result

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _overlaps(start: int, end: int, replacements: list[tuple[int, int, str]]) -> bool:
        return any(r[0] <= start < r[1] or start <= r[0] < end for r in replacements)

    @classmethod
    def _symbol_to_code(cls, symbol: str) -> Optional[str]:
        for sym, code in cls._SYMBOL_MAP:
            if symbol == sym:
                return code
        return None

    @staticmethod
    def _parse_number(raw: str) -> float:
        value = raw.strip()
        if "," in value and "." in value:
            value = value.replace(".", "").replace(",", ".")
        elif "," in value:
            if value.count(",") > 1:
                value = value.replace(",", "")
            else:
                whole, fraction = value.split(",", 1)
                value = f"{whole}.{fraction}" if len(fraction) in {1, 2} else f"{whole}{fraction}"
        elif "." in value:
            if value.count(".") > 1:
                value = value.replace(".", "")
            else:
                whole, fraction = value.split(".", 1)
                if len(fraction) == 3:
                    value = f"{whole}{fraction}"
        try:
            return float(value)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_multiplier(raw: str) -> float:
        v = raw.strip().lower()
        if v == "mm":
            return 1_000_000
        if v in {"m", "mi", "milhao", "milhão", "milhoes", "milhões"}:
            return 1_000_000
        if v in {"k", "mil"}:
            return 1_000
        return 1.0

    @classmethod
    def _format_value(cls, amount: float, currency: str) -> str:
        symbol = cls.SYMBOLS.get(currency, f"{currency} ")
        abs_amount = abs(amount)
        sign = "-" if amount < 0 else ""
        if abs_amount >= 1_000_000:
            return f"{sign}{symbol}{abs_amount / 1_000_000:.2f}M"
        if abs_amount >= 1_000:
            return f"{sign}{symbol}{abs_amount / 1_000:.2f}K"
        return f"{sign}{symbol}{abs_amount:.2f}"
