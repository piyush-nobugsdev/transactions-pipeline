from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.modules.transactions.domain.entities import TransactionStatus

_STATUS_ALIASES = {
    "success": TransactionStatus.SUCCESS,
    "successful": TransactionStatus.SUCCESS,
    "succeeded": TransactionStatus.SUCCESS,
    "complete": TransactionStatus.SUCCESS,
    "completed": TransactionStatus.SUCCESS,
    "paid": TransactionStatus.SUCCESS,
    "settled": TransactionStatus.SUCCESS,
    "posted": TransactionStatus.SUCCESS,
    "approved": TransactionStatus.SUCCESS,
    "cleared": TransactionStatus.SUCCESS,
    "failed": TransactionStatus.FAILED,
    "failure": TransactionStatus.FAILED,
    "declined": TransactionStatus.FAILED,
    "rejected": TransactionStatus.FAILED,
    "cancelled": TransactionStatus.FAILED,
    "canceled": TransactionStatus.FAILED,
    "error": TransactionStatus.FAILED,
    "pending": TransactionStatus.PENDING,
    "in progress": TransactionStatus.PENDING,
    "processing": TransactionStatus.PENDING,
    "authorized": TransactionStatus.PENDING,
    "authorised": TransactionStatus.PENDING,
    "on hold": TransactionStatus.PENDING,
    "initiated": TransactionStatus.PENDING,
    "queued": TransactionStatus.PENDING,
}

_CURRENCY_ALIASES = {
    "usd": "USD",
    "us dollar": "USD",
    "us dollars": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "$": "USD",
    "us$": "USD",
    "us dollar $": "USD",
    "inr": "INR",
    "indian rupee": "INR",
    "indian rupees": "INR",
    "rupee": "INR",
    "rupees": "INR",
    "rs": "INR",
    "₹": "INR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "€": "EUR",
    "gbp": "GBP",
    "british pound": "GBP",
    "british pounds": "GBP",
    "pound sterling": "GBP",
    "£": "GBP",
    "jpy": "JPY",
    "japanese yen": "JPY",
    "yen": "JPY",
    "¥": "JPY",
    "cad": "CAD",
    "canadian dollar": "CAD",
    "aud": "AUD",
    "australian dollar": "AUD",
    "chf": "CHF",
    "swiss franc": "CHF",
    "cny": "CNY",
    "chinese yuan": "CNY",
}

_CATEGORY_ALIASES = {
    "food": "Food & Dining",
    "dining": "Food & Dining",
    "food and dining": "Food & Dining",
    "groceries": "Food & Dining",
    "restaurant": "Food & Dining",
    "restaurants": "Food & Dining",
    "travel": "Travel",
    "transport": "Travel",
    "transportation": "Travel",
    "software": "Software & Subscriptions",
    "subscriptions": "Software & Subscriptions",
    "software subscriptions": "Software & Subscriptions",
    "office": "Office Supplies",
    "supplies": "Office Supplies",
    "office supplies": "Office Supplies",
    "utility": "Utilities",
    "utilities": "Utilities",
    "housing": "Rent",
    "rent": "Rent",
    "banking": "Fees & Banking",
    "fees": "Fees & Banking",
    "bank fees": "Fees & Banking",
    "fees and banking": "Fees & Banking",
    "medical": "Healthcare",
    "health": "Healthcare",
    "healthcare": "Healthcare",
    "other": "Other",
    "misc": "Other",
    "miscellaneous": "Other",
}

_AMOUNT_CURRENCY_MARKERS = ("USD", "INR", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY")
_AMOUNT_SYMBOLS = "$₹€£¥"


def normalize_status(value: str) -> TransactionStatus:
    normalized = _normalize_words(value)
    try:
        return _STATUS_ALIASES[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported transaction status: {value.strip()}") from exc


def normalize_currency(value: str) -> str:
    stripped = value.strip()
    if stripped in {"$", "US$"}:
        return "USD"
    if stripped == "₹":
        return "INR"
    if stripped == "€":
        return "EUR"
    if stripped == "£":
        return "GBP"
    if stripped == "¥":
        return "JPY"
    normalized = _normalize_words(stripped)
    currency = _CURRENCY_ALIASES.get(normalized, stripped.upper())
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("invalid currency")
    return currency


def normalize_amount(value: str) -> Decimal:
    normalized = value.strip()
    for marker in _AMOUNT_CURRENCY_MARKERS:
        normalized = re.sub(rf"(?i)\b{marker}\b", "", normalized)
    normalized = re.sub(r"(?i)\b(?:rs\.?|rupees?)\b", "", normalized)
    for symbol in _AMOUNT_SYMBOLS:
        normalized = normalized.replace(symbol, "")
    normalized = re.sub(r"\s+", "", normalized)
    if "," in normalized and "." in normalized:
        decimal_separator = "," if normalized.rfind(",") > normalized.rfind(".") else "."
        grouping_separator = "." if decimal_separator == "," else ","
        normalized = normalized.replace(grouping_separator, "")
        if decimal_separator == ",":
            normalized = normalized.replace(",", ".")
    elif "," in normalized:
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3}", normalized):
            normalized = normalized.replace(",", "")
        else:
            normalized = normalized.replace(",", ".")
    amount = Decimal(normalized)
    if not amount.is_finite():
        raise InvalidOperation
    return amount


def normalize_category(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return "Uncategorised"
    return _CATEGORY_ALIASES.get(_normalize_words(stripped), stripped)


def _normalize_words(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
