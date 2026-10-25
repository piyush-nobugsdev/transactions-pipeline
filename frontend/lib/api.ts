import type { AuditJob, CSVMappingField, CSVMappingPreview } from "@/types/audit";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function getErrorMessage(data: unknown, fallback: string) {
  if (typeof data !== "object" || data === null) {
    return fallback;
  }

  const payload = data as {
    error?: { message?: unknown };
    detail?: string | { message?: unknown };
  };
  const message =
    payload.error?.message ??
    (typeof payload.detail === "object"
      ? payload.detail.message
      : payload.detail);
  return typeof message === "string" ? message : fallback;
}

export async function previewAuditFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/v1/audits/upload/preview`, {
    method: "POST",
    body: formData,
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getErrorMessage(data, "Unable to inspect this CSV."));
  }
  return data as CSVMappingPreview;
}

export async function uploadAuditFile(
  file: File,
  businessLabel: string | undefined,
  mappings: Partial<Record<CSVMappingField, string>>,
) {
  const formData = new FormData();
  formData.append("file", file);

  if (businessLabel && businessLabel.trim()) {
    formData.append("business_label", businessLabel.trim());
  }
  formData.append("column_mappings", JSON.stringify(mappings));

  const response = await fetch(`${API_BASE_URL}/v1/audits/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(getErrorMessage(data, "Upload failed."));
  }

  return (await response.json()) as AuditJob;
}

export async function getAuditStatus(jobId: string) {
  const response = await fetch(`${API_BASE_URL}/v1/audits/${jobId}/status`);

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(getErrorMessage(data, "Unable to fetch job status."));
  }

  return (await response.json()) as AuditJob;
}
