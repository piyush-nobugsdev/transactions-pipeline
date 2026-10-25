"use client";

import { useEffect, useRef, useState } from "react";
import { getAuditStatus, previewAuditFile, uploadAuditFile } from "@/lib/api";
import {
  CSV_MAPPING_FIELDS,
  type AuditJob,
  type CSVMappingField,
  type CSVMappingPreview,
} from "@/types/audit";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const FINAL_STATUSES = new Set(["completed", "failed"]);

const statusLabels: Record<AuditJob["status"], string> = {
  pending: "Queued",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
};

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CSVMappingPreview | null>(null);
  const [mappings, setMappings] = useState<
    Partial<Record<CSVMappingField, string>>
  >({});
  const [manuallySelectedMappings, setManuallySelectedMappings] = useState<
    Set<CSVMappingField>
  >(new Set());
  const [businessLabel, setBusinessLabel] = useState("");
  const [job, setJob] = useState<AuditJob | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);
  const previewRequestRef = useRef(0);

  useEffect(() => {
    if (!job || FINAL_STATUSES.has(job.status)) {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const nextJob = await getAuditStatus(job.id);
        setJob(nextJob);
        if (FINAL_STATUSES.has(nextJob.status)) {
          window.clearInterval(interval);
          setIsPolling(false);
        }
      } catch (pollError) {
        window.clearInterval(interval);
        setIsPolling(false);
        setError(
          pollError instanceof Error
            ? pollError.message
            : "The job status could not be refreshed.",
        );
      }
    }, 2000);

    return () => window.clearInterval(interval);
  }, [job]);

  const handleFileSelection = async (file: File | null) => {
    const requestId = ++previewRequestRef.current;
    setPreview(null);
    setMappings({});
    setManuallySelectedMappings(new Set());
    setError("");
    setIsPreviewing(false);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Only CSV files can be uploaded for the audit flow.");
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError("The selected file is larger than the 10 MB upload limit.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setIsPreviewing(true);
    try {
      const csvPreview = await previewAuditFile(file);
      if (previewRequestRef.current !== requestId) return;
      setPreview(csvPreview);
      const suggestedMappings: Partial<Record<CSVMappingField, string>> = {};
      for (const { key } of CSV_MAPPING_FIELDS) {
        const source = csvPreview.suggested_mappings[key];
        if (source) {
          suggestedMappings[key] = source;
        }
      }
      setMappings(suggestedMappings);
    } catch (previewError) {
      if (previewRequestRef.current !== requestId) return;
      setError(
        previewError instanceof Error
          ? previewError.message
          : "The CSV could not be inspected.",
      );
      setSelectedFile(null);
    } finally {
      if (previewRequestRef.current === requestId) {
        setIsPreviewing(false);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !preview) {
      setError("Select and preview a CSV file before uploading.");
      return;
    }

    setError("");
    setIsUploading(true);

    try {
      const createdJob = await uploadAuditFile(
        selectedFile,
        businessLabel,
        mappings,
      );
      setJob(createdJob);
      setIsPolling(!FINAL_STATUSES.has(createdJob.status));
      setBusinessLabel("");
      setSelectedFile(null);
      setPreview(null);
      setMappings({});
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "The file could not be uploaded.",
      );
    } finally {
      setIsUploading(false);
    }
  };

  const hasRequiredMappings =
    preview !== null &&
    CSV_MAPPING_FIELDS.filter((field) => field.required).every(
      ({ key }) => Boolean(mappings[key]),
    );
  const hasDuplicateMappings =
    new Set(Object.values(mappings)).size !== Object.values(mappings).length;
  const canUpload =
    Boolean(selectedFile && preview) &&
    hasRequiredMappings &&
    !hasDuplicateMappings &&
    preview?.blocking_issues.length === 0;

  const changeMapping = (field: CSVMappingField, source: string) => {
    setMappings((current) => {
      const next = { ...current };
      if (!source) {
        delete next[field];
      } else {
        next[field] = source;
      }
      return next;
    });
    setManuallySelectedMappings((selected) => new Set(selected).add(field));
  };

  return (
    <main className="page-shell">
      <section className="panel hero-panel">
        <div className="eyebrow">LedgerGuard</div>
        <h1>Upload a transaction CSV</h1>
        <p className="subtitle">
          Send a file to the backend, track the audit job, and monitor the result
          as it moves through the pipeline.
        </p>

        <div className="upload-box">
          <input
            ref={inputRef}
            id="csv-upload"
            type="file"
            accept=".csv,text/csv"
            disabled={isUploading}
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              event.currentTarget.value = "";
              void handleFileSelection(file);
            }}
          />
          <label htmlFor="csv-upload">
            <span className="upload-icon">⇪</span>
            {selectedFile ? selectedFile.name : "Choose CSV file"}
          </label>
        </div>

        <div className="field-row">
          <label htmlFor="businessLabel">Business label</label>
          <input
            id="businessLabel"
            type="text"
            value={businessLabel}
            placeholder="Acme Books"
            onChange={(event) => setBusinessLabel(event.target.value)}
          />
        </div>

        {selectedFile ? (
          <div className="meta-row">
            <span>{selectedFile.name}</span>
            <span>{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</span>
          </div>
        ) : null}

        {isPreviewing ? (
          <p className="muted-message">Inspecting CSV headers and sample rows…</p>
        ) : null}

        {preview ? (
          <section className="mapping-section" aria-labelledby="mapping-title">
            <div>
              <h2 id="mapping-title">Review column mapping</h2>
              <p className="muted-message">
                Automatic matches are preselected. Confirm or change any
                field before processing.
              </p>
            </div>

            {preview.blocking_issues.map((issue) => (
              <div className="error-box" key={issue}>
                {issue}
              </div>
            ))}

            <div className="mapping-list">
              {CSV_MAPPING_FIELDS.map(({ key, label, required }) => {
                const isMissing = required && !mappings[key];
                const isAutomatic =
                  preview.mapping_status[key] === "automatic" &&
                  mappings[key] === preview.suggested_mappings[key] &&
                  !manuallySelectedMappings.has(key);
                const otherSelections = new Set(
                  Object.entries(mappings)
                    .filter(([selectedField]) => selectedField !== key)
                    .map(([, source]) => source),
                );

                return (
                  <div className="mapping-row" key={key}>
                    <label htmlFor={`mapping-${key}`}>
                      {label}
                      {required ? <span className="required-mark"> *</span> : null}
                    </label>
                    <select
                      id={`mapping-${key}`}
                      value={mappings[key] ?? ""}
                      aria-invalid={isMissing || hasDuplicateMappings}
                      aria-describedby={`mapping-hint-${key}`}
                      onChange={(event) =>
                        changeMapping(key, event.target.value)
                      }
                    >
                      <option value="">
                        {required ? "Select a source column" : "Not mapped (optional)"}
                      </option>
                      {preview.headers.map((header) => (
                        <option
                          key={header}
                          value={header}
                          disabled={otherSelections.has(header)}
                        >
                          {header}
                        </option>
                      ))}
                    </select>
                    <span
                      className={`mapping-hint${isMissing ? " mapping-error" : ""}`}
                      id={`mapping-hint-${key}`}
                    >
                      {isMissing
                        ? preview.mapping_status[key] === "ambiguous"
                          ? `Several columns could match: ${preview.candidates[key].join(", ")}. Select one.`
                          : "Required mapping is missing."
                        : isAutomatic
                          ? "Matched automatically — confirm this is correct."
                          : mappings[key]
                            ? "Selected manually."
                            : "Optional field."}
                    </span>
                  </div>
                );
              })}
            </div>

            {hasDuplicateMappings ? (
              <p className="mapping-error" role="alert">
                Each source column can only be used once.
              </p>
            ) : null}

            <div className="csv-preview">
              <h3>CSV preview</h3>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      {preview.headers.map((header) => (
                        <th key={header}>{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.preview_rows.length ? (
                      preview.preview_rows.map((row, rowIndex) => (
                        <tr key={rowIndex}>
                          {preview.headers.map((header) => (
                            <td key={header}>{row[header]}</td>
                          ))}
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={preview.headers.length}>
                          No transaction rows found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        ) : null}

        {error ? <div className="error-box">{error}</div> : null}

        <button
          type="button"
          className="primary-button"
          onClick={handleUpload}
          disabled={isUploading || isPreviewing || !canUpload}
        >
          {isUploading ? "Uploading..." : "Upload and process"}
        </button>
      </section>

      <section className="panel status-panel">
        <div className="status-header">
          <h2>Audit status</h2>
          {job ? (
            <span className={`status-pill status-${job.status}`}>
              {statusLabels[job.status]}
            </span>
          ) : (
            <span className="status-pill status-idle">Idle</span>
          )}
        </div>

        {job ? (
          <div className="job-card">
            <div className="job-line">
              <span className="label">Job ID</span>
              <strong>{job.id}</strong>
            </div>
            <div className="job-line">
              <span className="label">File</span>
              <strong>{job.filename}</strong>
            </div>
            <div className="job-line">
              <span className="label">Created</span>
              <strong>{new Date(job.created_at).toLocaleString()}</strong>
            </div>
            <div className="job-line">
              <span className="label">Processing</span>
              <strong>{isPolling ? "In progress" : "Awaiting next update"}</strong>
            </div>
            {job.error_message ? (
              <div className="job-line error-line">
                <span className="label">Error</span>
                <strong>{job.error_message}</strong>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="empty-state">
            No file has been uploaded yet. Choose a CSV to start an audit.
          </p>
        )}
      </section>
    </main>
  );
}
