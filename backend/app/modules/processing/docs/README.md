# Processing Module

The Processing module's authoritative contract, implementation status, CSV rules, lifecycle, testing instructions, and remaining work are documented in [`docs/processing-module.md`](../../../../../docs/processing-module.md).

This module currently validates and cleans audit CSV data, persists normalized transactions through the Transactions repository contract, and records job completion or failure. Anomaly detection, AI, summaries, retries, and export are not implemented yet.
