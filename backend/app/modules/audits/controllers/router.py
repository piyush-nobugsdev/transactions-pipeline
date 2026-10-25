import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.modules.processing.domain.services.csv_mapper import CSVMappingError

from ..application.dto.request.job_requests import CreateJobRequest
from ..application.dto.response.job_responses import JobListResponse, JobResponse
from ..application.mappers.job_mapper import to_job_response
from ..application.services.csv_mapping_service import CSVMappingService
from ..application.services.job_service import JobService
from .dependencies import get_job_service

router = APIRouter(prefix="/v1/audits", tags=["audits"])


@router.post("/upload/preview")
async def preview_audit_upload(
    file: UploadFile = File(...),
    mapping_service: CSVMappingService = Depends(),
) -> dict[str, object]:
    content = await _read_upload(file)
    try:
        preview = mapping_service.preview(content)
    except CSVMappingError as exc:
        raise BadRequestError(str(exc)) from exc
    return preview.as_dict()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    request: CreateJobRequest,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    return to_job_response(await service.create_job(request))


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_audit(
    file: UploadFile = File(...),
    business_label: str | None = Form(default=None),
    column_mappings: str | None = Form(default=None),
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    content = await _read_upload(file)
    mappings = _parse_column_mappings(column_mappings)
    content_type = file.content_type or "application/octet-stream"
    try:
        job = await service.create_uploaded_job(
            filename=file.filename or "upload.csv",
            business_label=business_label,
            content=content,
            content_type=content_type,
            column_mappings=mappings,
        )
    except CSVMappingError as exc:
        raise BadRequestError(str(exc)) from exc
    return to_job_response(job)


@router.get("", response_model=JobListResponse)
async def list_audits(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: JobService = Depends(get_job_service),
) -> JobListResponse:
    jobs = await service.list_jobs(offset=offset, limit=limit)
    return JobListResponse(
        items=[to_job_response(job) for job in jobs],
        offset=offset,
        limit=limit,
    )


@router.get("/{job_id}/status", response_model=JobResponse)
async def get_audit_status(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    return to_job_response(await service.get_job(job_id))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
) -> Response:
    await service.delete_job(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read()
    if not content:
        raise BadRequestError("The uploaded file must not be empty.")
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise BadRequestError("The uploaded file exceeds the configured size limit.")
    return content


def _parse_column_mappings(value: str | None) -> dict[str, str | None] | None:
    if value is None:
        return None
    try:
        mappings = json.loads(value)
    except json.JSONDecodeError as exc:
        raise BadRequestError("Column mappings must be valid JSON.") from exc
    if not isinstance(mappings, dict) or any(
        not isinstance(field, str) or (source is not None and not isinstance(source, str))
        for field, source in mappings.items()
    ):
        raise BadRequestError("Column mappings must map transaction fields to CSV header names.")
    return mappings
