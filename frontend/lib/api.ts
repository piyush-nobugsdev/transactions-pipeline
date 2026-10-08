import type { AuditJob } from "@/types/audit";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function uploadAuditFile(file: File, businessLabel?: string) {
  const formData = new FormData();
  formData.append("file", file);

  if (businessLabel && businessLabel.trim()) {
    formData.append("business_label", businessLabel.trim());
  }

  const response = await fetch(`${API_BASE_URL}/v1/audits/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.message ?? "Upload failed.";
    throw new Error(message);
  }

  return (await response.json()) as AuditJob;
}

export async function getAuditStatus(jobId: string) {
  const response = await fetch(`${API_BASE_URL}/v1/audits/${jobId}/status`);

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.message ?? "Unable to fetch job status.";
    throw new Error(message);
  }

  return (await response.json()) as AuditJob;
}
