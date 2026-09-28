from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.modules.transactions.domain.entities import TransactionStatus


class CSVValidationError(ValueError):
    pass


REQUIRED_COLUMNS = {"date", "merchant", "amount", "currency", "status", "account_id"}
OPTIONAL_COLUMNS = {"txn_id", "category"}
SUPPORTED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


def clean_transactions(content: bytes, *, job_id: UUID) -> tuple[int, list[dict[str, object]]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CSVValidationError("CSV file must use UTF-8 encoding.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CSVValidationError("CSV file must include a header row.")

    normalized_headers = [header.strip().lower() for header in reader.fieldnames if header]
    if len(normalized_headers) != len(reader.fieldnames):
        raise CSVValidationError("CSV headers must be non-empty.")
    if len(normalized_headers) != len(set(normalized_headers)):
        raise CSVValidationError("CSV headers must be unique.")

    headers = set(normalized_headers)
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise CSVValidationError(
            "CSV file is missing required columns: " + ", ".join(sorted(missing))
        )
    unexpected = headers - SUPPORTED_COLUMNS
    if unexpected:
        raise CSVValidationError(
            "CSV file contains unsupported columns: " + ", ".join(sorted(unexpected))
        )

    reader.fieldnames = normalized_headers
    records: list[dict[str, object]] = []
    seen: set[tuple[str, date, Decimal, str]] = set()
    raw_count = 0

    for row_number, row in enumerate(reader, start=2):
        if not row or all(value is None or not value.strip() for value in row.values()):
            continue
        raw_count += 1
        if None in row:
            raise CSVValidationError(f"CSV row {row_number} has more values than the header.")
        if any(value is None for value in row.values()):
            raise CSVValidationError(f"CSV row {row_number} has missing values.")

        try:
            transaction_date = _parse_date(row["date"].strip())
            merchant = row["merchant"].strip()
            if not merchant:
                raise CSVValidationError(f"CSV row {row_number} has an empty merchant.")
            amount = _parse_amount(row["amount"].strip())
            if amount <= 0:
                raise CSVValidationError(f"CSV row {row_number} has a non-positive amount.")
            currency = row["currency"].strip().upper()
            if len(currency) != 3 or not currency.isalpha():
                raise CSVValidationError(f"CSV row {row_number} has an invalid currency.")
            status = TransactionStatus(row["status"].strip().upper())
            account_id = row["account_id"].strip()
            if not account_id:
                raise CSVValidationError(f"CSV row {row_number} has an empty account_id.")
        except (KeyError, InvalidOperation, ValueError) as exc:
            if isinstance(exc, CSVValidationError):
                raise
            raise CSVValidationError(f"CSV row {row_number} contains an invalid value.") from exc

        txn_id = (row.get("txn_id") or "").strip() or None
        category = (row.get("category") or "").strip() or "Uncategorised"
        duplicate_key = (txn_id or "", transaction_date, amount, merchant)
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)

        records.append(
            {
                "job_id": job_id,
                "txn_id": txn_id,
                "date": transaction_date,
                "merchant": merchant,
                "amount": amount,
                "currency": currency,
                "status": status,
                "category": category,
                "account_id": account_id,
            }
        )

    return raw_count, records


def _parse_date(value: str) -> date:
    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    raise ValueError("unsupported date format")


def _parse_amount(value: str) -> Decimal:
    normalized = value.replace(",", "").replace("$", "").replace("₹", "").strip()
    amount = Decimal(normalized)
    if not amount.is_finite():
        raise InvalidOperation
    return amount
