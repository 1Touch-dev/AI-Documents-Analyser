"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import {
  deleteDocument,
  getBatchStatus,
  listDocuments,
  type BatchStatusResponse,
  type DocumentItem,
  type UploadBatchResponse,
  uploadBatch,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

type NormalizedStatus = "ready" | "processing" | "failed";

function normalizeStatus(status?: string): NormalizedStatus {
  const value = (status || "").toLowerCase();
  if (["ready", "processed", "completed", "complete", "success", "succeeded"].includes(value)) {
    return "ready";
  }
  if (["processing", "pending", "queued", "uploading", "in_progress"].includes(value)) {
    return "processing";
  }
  return "failed";
}

export default function DocumentsPage() {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [category, setCategory] = useState("general");
  const [uploadSummary, setUploadSummary] = useState<UploadBatchResponse | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const metrics = useMemo(() => {
    const ready = documents.filter((d) => normalizeStatus(d.status) === "ready").length;
    const processing = documents.filter((d) => normalizeStatus(d.status) === "processing").length;
    const failed = documents.filter((d) => normalizeStatus(d.status) === "failed").length;
    const totalSizeMb = documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0) / (1024 * 1024);
    return { total: documents.length, ready, processing, failed, totalSizeMb };
  }, [documents]);

  async function refreshDocuments(showRefreshState = false) {
    if (showRefreshState) setIsRefreshing(true);
    try {
      const res = await listDocuments(token ?? undefined);
      setDocuments(res.documents);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents.");
    } finally {
      setIsLoading(false);
      if (showRefreshState) setIsRefreshing(false);
    }
  }

  useEffect(() => {
    refreshDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!uploadSummary?.batch_id || !token) return;

    let timer: number | undefined;
    let cancelled = false;
    let pollCount = 0;
    let sameProcessingCount = 0;
    let lastProcessing = -1;
    const MAX_POLLS = 120; // ~3 minutes at 1.5s interval
    const MAX_STAGNANT_POLLS = 20; // stop if processing count never changes

    const poll = async () => {
      try {
        const status = await getBatchStatus(uploadSummary.batch_id, token ?? undefined);
        if (cancelled) return;
        setBatchStatus(status);

        const completed = status.processing === 0 || status.ready + status.failed >= status.total;
        if (completed) {
          await refreshDocuments();
          return;
        }

        pollCount += 1;
        if (status.processing === lastProcessing) {
          sameProcessingCount += 1;
        } else {
          sameProcessingCount = 0;
          lastProcessing = status.processing;
        }

        if (pollCount >= MAX_POLLS || sameProcessingCount >= MAX_STAGNANT_POLLS) {
          await refreshDocuments();
          return;
        }

        if (status.processing > 0) {
          timer = window.setTimeout(poll, 1500);
        }
      } catch {
        // Polling can fail transiently while backend catches up.
        pollCount += 1;
        if (pollCount < MAX_POLLS) {
          timer = window.setTimeout(poll, 2000);
        }
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadSummary?.batch_id, token]);

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFiles(Array.from(event.target.files || []));
  }

  async function onUpload() {
    if (!selectedFiles.length) {
      setError("Please select at least one file.");
      return;
    }
    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadBatch(selectedFiles, category, token ?? undefined);
      setUploadSummary(result);
      setSelectedFiles([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function onDelete(documentId: string) {
    setError(null);
    try {
      await deleteDocument(documentId, token ?? undefined);
      await refreshDocuments(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-white">Documents</h2>
        <p className="text-sm text-slate-300">
          Full migration baseline: upload, metrics, polling status, and delete.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Total</p>
          <p className="mt-1 text-2xl font-semibold text-white">{metrics.total}</p>
        </article>
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Ready</p>
          <p className="mt-1 text-2xl font-semibold text-emerald-300">{metrics.ready}</p>
        </article>
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Processing</p>
          <p className="mt-1 text-2xl font-semibold text-amber-300">{metrics.processing}</p>
        </article>
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Total Size</p>
          <p className="mt-1 text-2xl font-semibold text-cyan-200">{metrics.totalSizeMb.toFixed(1)} MB</p>
        </article>
      </div>

      <div className="rounded-xl border border-white/15 bg-white/5 p-5">
        <h3 className="text-sm font-semibold text-white">Batch Upload</h3>
        <p className="mt-1 text-xs text-slate-300">
          Upload multiple files (`PDF`, `DOCX`, `PPTX`, `XLSX`, `CSV`, `TXT`, `JSON`) and track processing.
        </p>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_180px_140px]">
          <input
            type="file"
            multiple
            onChange={onFileChange}
            className="rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
          />
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="category"
            className="rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
          />
          <button
            onClick={onUpload}
            disabled={isUploading}
            className="rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {isUploading ? "Uploading..." : "Upload"}
          </button>
        </div>
        {!!selectedFiles.length && (
          <p className="mt-2 text-xs text-slate-300">{selectedFiles.length} file(s) selected.</p>
        )}
        {uploadSummary && (
          <p className="mt-2 text-xs text-cyan-100">
            Batch submitted: accepted {uploadSummary.accepted}, duplicates {uploadSummary.duplicates},
            rejected {uploadSummary.rejected}
          </p>
        )}
        {batchStatus && (
          <p className="mt-1 text-xs text-slate-300">
            Processing status: ready {batchStatus.ready} / processing {batchStatus.processing} / failed{" "}
            {batchStatus.failed}
          </p>
        )}
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      <div className="overflow-hidden rounded-xl border border-white/15 bg-white/5">
        <table className="w-full text-left text-sm">
          <thead className="bg-white/10 text-slate-200">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Size</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id} className="border-t border-white/10 text-slate-100">
                {(() => {
                  const normalizedStatus = normalizeStatus(doc.status);
                  const statusClass =
                    normalizedStatus === "ready"
                      ? "bg-emerald-500/20 text-emerald-200"
                      : normalizedStatus === "processing"
                      ? "bg-amber-500/20 text-amber-200"
                      : "bg-red-500/20 text-red-200";
                  return (
                    <>
                <td className="px-4 py-3">{doc.title}</td>
                <td className="px-4 py-3">{doc.category || "-"}</td>
                <td className="px-4 py-3">{doc.file_type}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${statusClass}`}>
                    {normalizedStatus}
                  </span>
                </td>
                <td className="px-4 py-3">{((doc.file_size || 0) / 1024).toFixed(1)} KB</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => onDelete(doc.id)}
                    className="rounded-md border border-red-300/40 px-2 py-1 text-xs text-red-200 hover:bg-red-500/10"
                  >
                    Delete
                  </button>
                </td>
                    </>
                  );
                })()}
              </tr>
            ))}
            {!documents.length ? (
              <tr>
                <td className="px-4 py-4 text-slate-300" colSpan={6}>
                  {isLoading ? "Loading documents..." : "No documents available."}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <button
        onClick={() => refreshDocuments(true)}
        disabled={isRefreshing}
        className="rounded-lg border border-white/25 px-4 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-60"
      >
        {isRefreshing ? "Refreshing..." : "Refresh"}
      </button>
    </section>
  );
}

