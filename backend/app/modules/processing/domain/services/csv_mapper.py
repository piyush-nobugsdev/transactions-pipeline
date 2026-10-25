from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

CANONICAL_FIELDS = (
    "date",
    "merchant",
    "amount",
    "currency",
    "status",
    "account_id",
    "txn_id",
    "category",
)
REQUIRED_FIELDS = CANONICAL_FIELDS[:6]
PREVIEW_ROW_LIMIT = 5

_ALIASES = {
    "date": {
        "date",
        "transaction date",
        "txn date",
        "posting date",
        "value date",
    },
    "merchant": {
        "merchant",
        "description",
        "narration",
        "particulars",
        "transaction details",
        "transaction description",
        "payee",
        "counterparty",
    },
    "amount": {
        "amount",
        "transaction amount",
        "transaction value",
        "amount inr",
        "amount usd",
    },
    "currency": {"currency", "currency code", "transaction currency", "txn currency"},
    "status": {"status", "transaction status", "txn status", "transaction state"},
    "account_id": {
        "account id",
        "account number",
        "account no",
        "account",
        "acct number",
        "acct no",
    },
    "txn_id": {
        "txn id",
        "transaction id",
        "transaction reference",
        "reference number",
        "reference",
        "utr",
    },
    "category": {"category", "transaction category"},
}
_DEBIT_HEADERS = {"debit", "dr", "withdrawal", "withdrawal amount"}
_CREDIT_HEADERS = {"credit", "cr", "deposit", "deposit amount"}


class CSVMappingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CSVMappingPreview:
    headers: list[str]
    rows: list[dict[str, str]]
    mappings: dict[str, str | None]
    mapping_status: dict[str, str]
    candidates: dict[str, list[str]]
    blocking_issues: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "headers": self.headers,
            "preview_rows": self.rows,
            "suggested_mappings": self.mappings,
            "mapping_status": self.mapping_status,
            "candidates": self.candidates,
            "blocking_issues": self.blocking_issues,
        }


def preview_csv_mapping(content: bytes) -> CSVMappingPreview:
    headers, rows = _read_csv(content)
    normalized_headers = [_normalize_header(header) for header in headers]
    candidates = {
        field: [
            header
            for header, normalized in zip(headers, normalized_headers, strict=True)
            if normalized in _ALIASES[field]
        ]
        for field in CANONICAL_FIELDS
    }

    source_owners: dict[str, list[str]] = {}
    for field, sources in candidates.items():
        for source in sources:
            source_owners.setdefault(source, []).append(field)

    mappings: dict[str, str | None] = {}
    mapping_status: dict[str, str] = {}
    for field, sources in candidates.items():
        if len(sources) == 1 and len(source_owners[sources[0]]) == 1:
            mappings[field] = sources[0]
            mapping_status[field] = "automatic"
        elif sources:
            mappings[field] = None
            mapping_status[field] = "ambiguous"
        else:
            mappings[field] = None
            mapping_status[field] = "missing"

    header_set = set(normalized_headers)
    has_debit = any(_is_flow_column(header, _DEBIT_HEADERS, "debit", "dr") for header in header_set)
    has_credit = any(_is_flow_column(header, _CREDIT_HEADERS, "credit", "cr") for header in header_set)
    blocking_issues = []
    if has_debit and has_credit:
        blocking_issues.append(
            "This CSV has separate debit and credit columns. That bank-statement format is not supported yet; "
            "convert it to one signed transaction amount column before uploading."
        )

    return CSVMappingPreview(
        headers=headers,
        rows=rows,
        mappings=mappings,
        mapping_status=mapping_status,
        candidates=candidates,
        blocking_issues=blocking_issues,
    )


def canonicalize_csv(content: bytes, mappings: dict[str, str | None]) -> bytes:
    headers, _ = _read_csv(content)

    if any(
        not isinstance(field, str) or (source is not None and (not isinstance(source, str) or not source))
        for field, source in mappings.items()
    ):
        raise CSVMappingError("Each selected mapping must identify one CSV column.")

    unknown_fields = set(mappings) - set(CANONICAL_FIELDS)
    if unknown_fields:
        raise CSVMappingError("Unsupported transaction fields: " + ", ".join(sorted(unknown_fields)) + ".")

    selected_mappings = {field: source for field, source in mappings.items() if source is not None}
    invalid_sources = set(selected_mappings.values()) - set(headers)
    if invalid_sources:
        raise CSVMappingError("A selected source column is not present in the CSV header.")

    selected_sources = list(selected_mappings.values())
    if len(selected_sources) != len(set(selected_sources)):
        raise CSVMappingError("A source column cannot be mapped to more than one transaction field.")

    missing_fields = set(REQUIRED_FIELDS) - set(selected_mappings)
    if missing_fields:
        raise CSVMappingError("Map all required fields before uploading: " + ", ".join(sorted(missing_fields)) + ".")

    normalized_headers = [_normalize_header(header) for header in headers]
    debit_present = any(_is_flow_column(header, _DEBIT_HEADERS, "debit", "dr") for header in normalized_headers)
    credit_present = any(_is_flow_column(header, _CREDIT_HEADERS, "credit", "cr") for header in normalized_headers)
    if debit_present and credit_present:
        raise CSVMappingError(
            "This CSV has separate debit and credit columns. That bank-statement format is not supported yet; "
            "convert it to one signed transaction amount column before uploading."
        )

    source_indexes = {header: index for index, header in enumerate(headers)}
    output_fields = [field for field in CANONICAL_FIELDS if field in selected_mappings]
    try:
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""))
        next(reader)
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(output_fields)
        for row_number, row in enumerate(reader, start=2):
            if not row or all(not value.strip() for value in row):
                writer.writerow([""] * len(output_fields))
                continue
            if len(row) > len(headers):
                raise CSVMappingError(f"CSV row {row_number} has more values than the header.")
            if len(row) < len(headers):
                raise CSVMappingError(f"CSV row {row_number} has missing values.")
            writer.writerow([row[source_indexes[selected_mappings[field]]] for field in output_fields])
    except (csv.Error, UnicodeDecodeError) as exc:
        raise CSVMappingError("Could not parse this CSV. Check its UTF-8 encoding and CSV formatting.") from exc

    return output.getvalue().encode("utf-8")


def _read_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    try:
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""))
        headers = next(reader, None)
        if not headers:
            raise CSVMappingError("CSV file must include a header row.")
        normalized = [_normalize_header(header) for header in headers]
        if any(not header for header in normalized):
            raise CSVMappingError("CSV headers must be non-empty.")
        if len(normalized) != len(set(normalized)):
            raise CSVMappingError(
                "CSV contains duplicate or conflicting headers. Rename the duplicate columns and retry."
            )

        preview_rows = []
        for row_number, row in enumerate(reader, start=2):
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) > len(headers):
                raise CSVMappingError(f"CSV row {row_number} has more values than the header.")
            if len(row) < len(headers):
                raise CSVMappingError(f"CSV row {row_number} has missing values.")
            if len(preview_rows) < PREVIEW_ROW_LIMIT:
                preview_rows.append(dict(zip(headers, row, strict=True)))
        return headers, preview_rows
    except UnicodeDecodeError as exc:
        raise CSVMappingError("CSV file must use UTF-8 encoding.") from exc
    except csv.Error as exc:
        raise CSVMappingError("Could not parse this CSV. Check its UTF-8 encoding and CSV formatting.") from exc


def _normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", header.strip().lower()).strip()


def _is_flow_column(header: str, aliases: set[str], *tokens: str) -> bool:
    return header in aliases or any(header.startswith(f"{token} ") or header.endswith(f" {token}") for token in tokens)
