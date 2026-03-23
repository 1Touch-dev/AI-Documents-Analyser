"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getAnalyticsContent,
  getAnalyticsOverview,
  getAnalyticsStorage,
  listDocuments,
  type DocumentItem,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

function downloadFile(content: string, fileName: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export default function ExportDataPage() {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [content, setContent] = useState<Record<string, unknown> | null>(null);
  const [storage, setStorage] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      listDocuments(token ?? undefined, 500),
      getAnalyticsOverview(token ?? undefined),
      getAnalyticsContent(token ?? undefined),
      getAnalyticsStorage(token ?? undefined),
    ])
      .then(([docs, ov, ct, st]) => {
        setDocuments(docs.documents);
        setOverview(ov as unknown as Record<string, unknown>);
        setContent(ct as unknown as Record<string, unknown>);
        setStorage(st as unknown as Record<string, unknown>);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load export data."));
  }, [token]);

  const csvData = useMemo(() => {
    const headers = ["id", "title", "category", "uploaded_by", "timestamp", "file_type", "file_size", "chunk_count", "status"];
    const rows = documents.map((d) =>
      [
        d.id,
        d.title,
        d.category || "",
        d.uploaded_by || "",
        d.timestamp || "",
        d.file_type || "",
        String(d.file_size || 0),
        String(d.chunk_count || 0),
        d.status || "",
      ]
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(",")
    );
    return [headers.join(","), ...rows].join("\n");
  }, [documents]);

  const jsonData = useMemo(() => JSON.stringify(documents, null, 2), [documents]);

  const analyticsSummary = useMemo(
    () =>
      JSON.stringify(
        {
          overview,
          storage,
          content_summary: content,
        },
        null,
        2
      ),
    [content, overview, storage]
  );

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-white">Export Data (BI Integration)</h2>
        <p className="text-sm text-slate-300">
          Download document datasets and analytics summaries for Tableau/Power BI.
        </p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <div className="grid gap-4 md:grid-cols-3">
        <button
          type="button"
          onClick={() => downloadFile(csvData, "documents_export.csv", "text/csv")}
          className="rounded-xl border border-white/15 bg-white/5 p-5 text-left hover:bg-white/10"
        >
          <p className="text-sm font-semibold text-white">CSV (Tableau / Power BI)</p>
          <p className="mt-1 text-xs text-slate-300">Flat tabular export of all documents.</p>
        </button>
        <button
          type="button"
          onClick={() => downloadFile(jsonData, "documents_export.json", "application/json")}
          className="rounded-xl border border-white/15 bg-white/5 p-5 text-left hover:bg-white/10"
        >
          <p className="text-sm font-semibold text-white">JSON Export</p>
          <p className="mt-1 text-xs text-slate-300">Raw document objects for API pipelines.</p>
        </button>
        <button
          type="button"
          onClick={() => downloadFile(analyticsSummary, "analytics_summary.json", "application/json")}
          className="rounded-xl border border-white/15 bg-white/5 p-5 text-left hover:bg-white/10"
        >
          <p className="text-sm font-semibold text-white">Analytics Summary</p>
          <p className="mt-1 text-xs text-slate-300">Overview, storage, and content metrics.</p>
        </button>
      </div>

      <article className="rounded-xl border border-white/15 bg-white/5 p-4">
        <p className="text-xs text-slate-300">Export Preview</p>
        <p className="mt-1 text-sm text-slate-100">
          {documents.length} documents ready for export.
        </p>
      </article>
    </section>
  );
}

