# Insights Module

The Insights module owns deterministic merchant-based category suggestions and
currency-aware audit aggregates. It is designed to provide a complete
upload-to-report prototype without requiring an external AI provider.

## Category assignment

During processing, the module assigns a category to transactions whose uploaded
category is blank or `Uncategorised`. A user-provided category is preserved.
Classification is based on normalized merchant-name keywords, with an `Other`
fallback. The current categories are:

- Food & Dining
- Travel
- Software & Subscriptions
- Office Supplies
- Utilities
- Rent
- Fees & Banking
- Healthcare
- Other

These are deterministic heuristics, not AI classification. They are intended
for the prototype and may not correctly categorize every merchant. The frontend
labels them accordingly.

## Insights API

```text
GET /v1/insights/{job_id}
```

Returns the transaction count, successful transaction count, anomaly-flag
count, spend totals by currency, spend by category and currency, highest-value
successful transactions, and repeated merchants.

Spend totals, category totals, and highest-transaction rankings are grouped by
currency; the service never adds amounts across currencies. Failed and pending
transactions remain categorized and visible in transaction results, but only
`SUCCESS` transactions contribute to spend and merchant frequency insights.
Repeated-merchant grouping is case-insensitive and ignores punctuation.

The endpoint validates that the audit job exists and reads transactions in
pages of 500. The current implementation computes aggregates in application
memory; add database-side aggregation or a result snapshot before using it for
very large production jobs.

## Processing integration

The Processing application service depends on a `TransactionCategorizer`
protocol. The Celery composition boundary wires this to `InsightsService`,
which classifies and persists categories before job completion. Category
updates share the worker's unit of work with normalized transaction creation,
anomaly flags, and job completion.

## Tests and demo data

Unit tests cover category matching, preservation of supplied categories,
currency-separated spend aggregation, repeat merchants, and API responses.
[`examples/demo_transactions.csv`](../examples/demo_transactions.csv) provides
a small file for demonstrating successful categorization, duplicate and
outlier flags, a currency mismatch, and report insights.
