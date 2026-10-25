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

export const CSV_MAPPING_FIELDS = [
  { key: "date", label: "Date", required: true },
  { key: "merchant", label: "Merchant / description", required: true },
  { key: "amount", label: "Amount", required: true },
  { key: "currency", label: "Currency", required: true },
  { key: "status", label: "Transaction status", required: true },
  { key: "account_id", label: "Account number / ID", required: true },
  { key: "txn_id", label: "Transaction ID", required: false },
  { key: "category", label: "Category", required: false },
] as const;

export type CSVMappingField = (typeof CSV_MAPPING_FIELDS)[number]["key"];
export type CSVMappingStatus = "automatic" | "ambiguous" | "missing";

export type CSVMappingPreview = {
  headers: string[];
  preview_rows: Record<string, string>[];
  suggested_mappings: Record<CSVMappingField, string | null>;
  mapping_status: Record<CSVMappingField, CSVMappingStatus>;
  candidates: Record<CSVMappingField, string[]>;
  blocking_issues: string[];
};
