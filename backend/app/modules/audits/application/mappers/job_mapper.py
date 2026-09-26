from ...domain.entities import JobRecord
from ..dto.response.job_responses import JobResponse


def to_job_response(job: JobRecord) -> JobResponse:
    return JobResponse.model_validate(job)
