# Audits / Jobs OpenAPI Notes

The router is registered by the backend app factory and contributes the `audits` tag to the generated FastAPI OpenAPI document.

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/v1/audits` | Create a pending job from validated file metadata | `201 JobResponse` |
| `POST` | `/v1/audits/upload/preview` | Preview CSV headers, sample rows, and automatic mappings | `200` mapping preview |
| `POST` | `/v1/audits/upload` | Map, store, and queue a CSV audit | `201 JobResponse` |
| `GET` | `/v1/audits` | List jobs with offset/limit pagination | `200 JobListResponse` |
| `GET` | `/v1/audits/{job_id}/status` | Read the current job status | `200 JobResponse` |
| `DELETE` | `/v1/audits/{job_id}` | Delete a job | `204 No Content` |

The upload preview and upload routes accept multipart form data. Preview takes
`file`; upload takes `file`, optional `business_label`, and optional
`column_mappings` as a JSON object mapping canonical field names to original CSV
headers. See [README.md](README.md) for the mapping contract and supported
aliases.

Invalid CSVs and mappings return the shared application error response with an
actionable message. Unknown job IDs use the shared `RESOURCE_NOT_FOUND` response
contract.
