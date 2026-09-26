# Audits / Jobs OpenAPI Notes

The router is registered by the backend app factory and contributes the `audits` tag to the generated FastAPI OpenAPI document.

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/v1/audits` | Create a pending job from validated file metadata | `201 JobResponse` |
| `GET` | `/v1/audits` | List jobs with offset/limit pagination | `200 JobListResponse` |
| `GET` | `/v1/audits/{job_id}/status` | Read the current job status | `200 JobResponse` |
| `DELETE` | `/v1/audits/{job_id}` | Delete a job | `204 No Content` |

Validation failures use the shared `VALIDATION_ERROR` response contract. Unknown job IDs use the shared `RESOURCE_NOT_FOUND` response contract.

The current creation endpoint accepts metadata that represents a file already addressable by storage. It does not receive multipart CSV content or dispatch a worker yet; those concerns will be introduced with the storage and processing infrastructure milestones.
