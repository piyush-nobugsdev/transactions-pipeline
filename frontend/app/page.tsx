"use client";

import { useEffect, useRef, useState } from "react";
import { getAuditStatus, uploadAuditFile } from "@/lib/api";
import type { AuditJob } from "@/types/audit";

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
  const [businessLabel, setBusinessLabel] = useState("");
  const [job, setJob] = useState<AuditJob | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!job || FINAL_STATUSES.has(job.status)) {
      setIsPolling(false);
      return;
    }

    setIsPolling(true);
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

  const handleFileSelection = (file: File | null) => {
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

    setError("");
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Please select a CSV file to upload.");
      return;
    }

    setError("");
    setIsUploading(true);

    try {
      const createdJob = await uploadAuditFile(selectedFile, businessLabel);
      setJob(createdJob);
      setBusinessLabel("");
      setSelectedFile(null);
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
            onChange={(event) =>
              handleFileSelection(event.target.files?.[0] ?? null)
            }
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

        {error ? <div className="error-box">{error}</div> : null}

        <button
          type="button"
          className="primary-button"
          onClick={handleUpload}
          disabled={isUploading || !selectedFile}
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
