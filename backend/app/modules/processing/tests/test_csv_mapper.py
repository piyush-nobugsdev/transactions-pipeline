from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.audits.application.services.csv_mapping_service import CSVMappingService
from app.modules.processing.domain.services.csv_cleaner import clean_transactions
from app.modules.processing.domain.services.csv_mapper import (
    CSVMappingError,
    preview_csv_mapping,
)

JOB_ID = "00000000-0000-0000-0000-000000000001"


def test_standard_headers_are_mapped_and_existing_cleaning_behavior_is_preserved():
    content = (
        b"txn_id,date,merchant,amount,currency,status,category,account_id,notes\n"
        b"t-1,01-03-2026,Shop,$12.50,usd,SUCCESS,,acct-1,ignored\n"
        b"t-1,01-03-2026,Shop,$12.50,usd,SUCCESS,,acct-1,ignored\n"
    )
    service = CSVMappingService()
    preview = service.preview(content)

    assert preview.mappings["date"] == "date"
    assert preview.mapping_status["amount"] == "automatic"
    canonical_csv = service.canonicalize(content, preview.mappings)
    raw_count, records = clean_transactions(canonical_csv, job_id=UUID(JOB_ID))

    assert raw_count == 2
    assert len(records) == 1
    assert records[0]["amount"] == Decimal("12.50")
    assert records[0]["currency"] == "USD"
    assert records[0]["category"] == "Uncategorised"


def test_maps_common_bank_headers_and_ignores_unknown_columns():
    preview = preview_csv_mapping(
        b"Transaction Date,Description,Transaction Amount,Currency,Status,Account Number,Bank Branch\n"
        b"2026-01-01,Coffee Shop,9.50,INR,SUCCESS,acct-5,Main\n"
    )

    assert preview.mappings == {
        "date": "Transaction Date",
        "merchant": "Description",
        "amount": "Transaction Amount",
        "currency": "Currency",
        "status": "Status",
        "account_id": "Account Number",
        "txn_id": None,
        "category": None,
    }
    result = CSVMappingService().canonicalize(
        b"Transaction Date,Description,Transaction Amount,Currency,Status,Account Number,Bank Branch\n"
        b"2026-01-01,Coffee Shop,9.50,INR,SUCCESS,acct-5,Main\n",
        preview.mappings,
    )
    assert result.startswith(b"date,merchant,amount,currency,status,account_id\n")
    assert b"Bank Branch" not in result


def test_header_matching_trims_whitespace_and_ignores_case():
    preview = preview_csv_mapping(
        b"  tRaNsAcTiOn DaTe  , DESCRIPTION , transaction amount , "
        b"currency code, transaction status, Account No \n"
        b"2026-01-01,Shop,10,USD,SUCCESS,acct-1\n"
    )

    assert preview.mappings["date"] == "  tRaNsAcTiOn DaTe  "
    assert preview.mappings["merchant"] == " DESCRIPTION "
    assert preview.mappings["amount"] == " transaction amount "


def test_partial_aliases_allow_manual_mapping_and_keep_optional_columns_optional():
    content = (
        b"Transaction Date,Narration,Debit Value,ISO Currency,Result,Account No,Reference\n"
        b"2026-01-01,Grocer,25.00,inr,SUCCESS,acct-2,ref-9\n"
    )
    preview = preview_csv_mapping(content)
    assert preview.mappings["date"] == "Transaction Date"
    assert preview.mappings["merchant"] == "Narration"
    assert preview.mapping_status["amount"] == "missing"

    mappings = {
        **{field: source for field, source in preview.mappings.items() if source},
        "amount": "Debit Value",
        "currency": "ISO Currency",
        "status": "Result",
    }
    canonical = CSVMappingService().canonicalize(content, mappings)
    assert canonical.startswith(b"date,merchant,amount,currency,status,account_id,txn_id\n")


def test_duplicate_conflicting_headers_are_rejected():
    with pytest.raises(CSVMappingError, match="duplicate or conflicting headers"):
        preview_csv_mapping(b"Date, date ,Merchant,Amount,Currency,Status,Account Number\n")


def test_ambiguous_aliases_are_not_auto_selected_and_need_manual_resolution():
    content = (
        b"Date,Transaction Date,Merchant,Amount,Currency,Status,Account Number\n"
        b"2026-01-01,2026-01-01,Shop,10,USD,SUCCESS,acct-1\n"
    )
    preview = preview_csv_mapping(content)

    assert preview.mapping_status["date"] == "ambiguous"
    assert preview.mappings["date"] is None
    with pytest.raises(CSVMappingError, match="date is ambiguous"):
        CSVMappingService().canonicalize(content)

    mappings = {
        "date": "Transaction Date",
        "merchant": "Merchant",
        "amount": "Amount",
        "currency": "Currency",
        "status": "Status",
        "account_id": "Account Number",
    }
    assert (
        CSVMappingService()
        .canonicalize(content, mappings)
        .startswith(b"date,merchant,amount,currency,status,account_id\n")
    )


def test_missing_required_fields_have_actionable_validation_error():
    content = b"Date,Description,Amount\n2026-01-01,Shop,10\n"
    with pytest.raises(CSVMappingError, match="currency"):
        CSVMappingService().canonicalize(content)


def test_source_column_cannot_be_reused_for_multiple_fields():
    content = b"Date,Merchant,Amount,Currency,Status,Account Number\n2026-01-01,Shop,10,USD,SUCCESS,acct-1\n"
    mappings = {
        "date": "Date",
        "merchant": "Merchant",
        "amount": "Amount",
        "currency": "Currency",
        "status": "Status",
        "account_id": "Merchant",
    }
    with pytest.raises(CSVMappingError, match="cannot be mapped to more than one"):
        CSVMappingService().canonicalize(content, mappings)


def test_separate_debit_and_credit_columns_are_blocked_with_guidance():
    preview = preview_csv_mapping(
        b"Date,Description,Debit,Credit,Currency,Status,Account Number\n2026-01-01,Shop,10,,USD,SUCCESS,acct-1\n"
    )
    assert preview.blocking_issues
    with pytest.raises(CSVMappingError, match="separate debit and credit columns"):
        CSVMappingService().canonicalize(
            b"Date,Description,Debit,Credit,Currency,Status,Account Number\n2026-01-01,Shop,10,,USD,SUCCESS,acct-1\n"
        )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"\xff", "UTF-8"),
        (b"Date,Merchant,Amount\n2026-01-01,Shop,10,extra\n", "more values"),
        (b"Date,Merchant,Amount\n2026-01-01,Shop\n", "missing values"),
        (b"Date,,Amount\n2026-01-01,Shop,10\n", "non-empty"),
    ],
)
def test_invalid_csv_shapes_are_rejected(content, message):
    with pytest.raises(CSVMappingError, match=message):
        preview_csv_mapping(content)
