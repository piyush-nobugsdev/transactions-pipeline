from __future__ import annotations

from app.modules.processing.domain.services.csv_mapper import (
    CANONICAL_FIELDS,
    REQUIRED_FIELDS,
    CSVMappingError,
    CSVMappingPreview,
    canonicalize_csv,
    preview_csv_mapping,
)


class CSVMappingService:
    def preview(self, content: bytes) -> CSVMappingPreview:
        return preview_csv_mapping(content)

    def canonicalize(
        self,
        content: bytes,
        mappings: dict[str, str | None] | None = None,
    ) -> bytes:
        if mappings is None:
            preview = self.preview(content)
            if preview.blocking_issues:
                raise CSVMappingError(preview.blocking_issues[0])
            mappings = {field: source for field, source in preview.mappings.items() if field in CANONICAL_FIELDS}
            missing = [field for field in REQUIRED_FIELDS if not mappings.get(field)]
            if missing:
                details = []
                for field in missing:
                    sources = preview.candidates[field]
                    if sources:
                        details.append(f"{field} is ambiguous ({', '.join(sources)})")
                    else:
                        details.append(f"{field} is missing")
                raise CSVMappingError(
                    "Automatic column mapping is incomplete: "
                    + "; ".join(details)
                    + ". Preview the CSV and select the correct columns."
                )
        return canonicalize_csv(content, mappings)
