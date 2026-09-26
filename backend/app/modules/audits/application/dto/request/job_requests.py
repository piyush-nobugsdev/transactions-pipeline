from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    business_label: str | None = Field(default=None, max_length=255)
    file_hash: str = Field(min_length=64, max_length=64)
    s3_bucket: str = Field(min_length=1, max_length=255)
    s3_key: str = Field(min_length=1, max_length=1024)
    file_size_bytes: int = Field(ge=0)
    content_type: str = Field(min_length=1, max_length=100)
    expires_at: datetime

    @field_validator("file_hash")
    @classmethod
    def validate_file_hash(cls, value: str) -> str:
        normalized = value.lower()
        if any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("file_hash must be a SHA-256 hexadecimal digest")
        return normalized
