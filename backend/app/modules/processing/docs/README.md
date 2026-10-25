# Processing Module

The Processing module's authoritative contract, implementation status, CSV rules, lifecycle, testing instructions, and remaining work are documented in [`docs/processing-module.md`](../../../../../docs/processing-module.md).

The audit upload flow previews CSV files and maps recognized or user-selected
source columns to the canonical transaction schema before storage. This module
owns the pure header-matching/canonicalization logic, then validates and cleans
the canonical CSV during processing, persists normalized transactions through
the Transactions repository contract, and records job completion or failure.
Anomaly detection, AI, summaries, retries, and export are not implemented yet.
