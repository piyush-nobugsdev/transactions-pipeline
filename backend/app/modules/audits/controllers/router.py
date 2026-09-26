from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.core.config import settings
from app.core.exceptions import BadRequestError

from ..application.mappers.job_mapper import to_job_response
from ..application.services.job_service import JobService
from ..application.dto.request.job_requests import CreateJobRequest
from ..application.dto.response.job_responses import JobListResponse, JobResponse
from .dependencies import get_job_service

router = APIRouter(prefix="/v1/audits", tags=["audits"])


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
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    content = await file.read()
    if not content:
        raise BadRequestError("The uploaded file must not be empty.")
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise BadRequestError("The uploaded file exceeds the configured size limit.")
    content_type = file.content_type or "application/octet-stream"
    job = await service.create_uploaded_job(
        filename=file.filename or "upload.csv",
        business_label=business_label,
        content=content,
        content_type=content_type,
    )
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
