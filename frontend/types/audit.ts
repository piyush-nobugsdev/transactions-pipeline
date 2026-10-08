export type JobStatus = "pending" | "processing" | "completed" | "failed";

export type AuditJob = {
  id: string;
  filename: string;
  business_label: string | null;
  status: JobStatus;
  file_hash: string;
  file_size_bytes: number;
  content_type: string;
  created_at: string;
  completed_at: string | null;
  expires_at: string;
  error_message: string | null;
};
