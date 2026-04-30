"use client";

import { useEffect, useState } from "react";
import {
  listSavedReports, getSavedReport, saveReport,
  type SavedReportMeta, type SavedReportFull,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import {
  BookMarked, ChevronRight, Clock, Download, Loader2, X,
} from "lucide-react";

const TYPE_ICON: Record<string, string> = {
  financial: "📊", consulting: "💡", report: "📝",
};
const TYPE_COLOR: Record<string, string> = {
  financial:  "border-emerald-500/30 bg-emerald-500/5",
  consulting: "border-indigo-500/30  bg-indigo-500/5",
  report:     "border-amber-500/30   bg-amber-500/5",
};

function DownloadButton({ data, filename }: { data: unknown; filename: string }) {
  function download(type: "json" | "csv") {
    if (type === "json") {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `${filename}.json`; a.click();
      URL.revokeObjectURL(url);
    } else {
      const rows: string[] = ["field,value"];
      function flatten(obj: unknown, prefix = "") {
        if (typeof obj === "object" && obj !== null && !Array.isArray(obj)) {
          for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
            flatten(v, prefix ? `${prefix}.${k}` : k);
          }
        } else if (Array.isArray(obj)) {
          obj.forEach((v, i) => flatten(v, `${prefix}[${i}]`));
        } else {
          rows.push(`"${prefix}","${String(obj).replace(/"/g, '""')}"`);
        }
      }
      flatten(data);
      const blob = new Blob([rows.join("\n")], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `${filename}.csv`; a.click();
      URL.revokeObjectURL(url);
    }
  }
  return (
    <div className="flex gap-1.5">
      <button type="button" onClick={() => download("json")}
        className="flex items-center gap-1 rounded border border-white/15 bg-white/5 px-2 py-1 text-[11px] text-slate-200 hover:bg-white/10">
        <Download className="h-3 w-3" /> JSON
      </button>
      <button type="button" onClick={() => download("csv")}
        className="flex items-center gap-1 rounded border border-white/15 bg-white/5 px-2 py-1 text-[11px] text-slate-200 hover:bg-white/10">
        <Download className="h-3 w-3" /> CSV
      </button>
    </div>
  );
}

function ReportDetailModal({ report, onClose }: { report: SavedReportFull; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-white/15 bg-slate-900 p-6 shadow-2xl">
        <button type="button" onClick={onClose}
          className="absolute right-4 top-4 rounded-full border border-white/10 bg-white/5 p-1 text-slate-300 hover:bg-white/10">
          <X className="h-4 w-4" />
        </button>

        <div className="mb-4 flex items-center gap-3">
          <span className="text-2xl">{TYPE_ICON[report.report_type] ?? "📄"}</span>
          <div>
            <h3 className="text-lg font-semibold text-white">{report.title}</h3>
            <p className="text-xs text-slate-400">
              {report.report_type} · {report.provider ?? "openai"} ·{" "}
              <span className="font-mono">{report.model_used ?? "auto"}</span>
              {" · "}{report.created_at.slice(0, 10)}
            </p>
          </div>
        </div>

        <pre className="max-h-[60vh] overflow-y-auto rounded-xl bg-slate-950/80 p-4 text-xs text-slate-200">
          {JSON.stringify(report.data, null, 2)}
        </pre>

        <div className="mt-4 flex justify-end">
          <DownloadButton data={report.data} filename={`${report.report_type}-${report.id.slice(0, 8)}`} />
        </div>
      </div>
    </div>
  );
}

export default function SavedReportsPage() {
  const { token } = useAuth();
  const [reports, setReports] = useState<SavedReportMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<SavedReportFull | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    listSavedReports(token ?? undefined)
      .then((r) => setReports(r.reports))
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, [token]);

  async function openReport(id: string) {
    setLoadingDetail(true);
    try {
      const r = await getSavedReport(id, token ?? undefined);
      setSelected(r);
    } catch {
      // silent
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <section className="space-y-6">
      {selected && <ReportDetailModal report={selected} onClose={() => setSelected(null)} />}

      <div>
        <h2 className="text-2xl font-semibold text-white">Saved Reports</h2>
        <p className="mt-1 text-sm text-slate-400">
          Persistent workflow results stored in the database. Click any report to view or export.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading reports…
        </div>
      ) : reports.length === 0 ? (
        <div className="flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-white/15 bg-white/3 text-center p-8">
          <BookMarked className="mb-3 h-10 w-10 text-slate-600" />
          <p className="text-sm font-semibold text-slate-300">No saved reports yet</p>
          <p className="mt-1 text-xs text-slate-500">
            Run a workflow and click "Save Report" to persist results here.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => openReport(r.id)}
              className={`rounded-2xl border p-4 text-left transition hover:brightness-110 ${TYPE_COLOR[r.report_type] ?? "border-white/10 bg-white/5"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-xl">{TYPE_ICON[r.report_type] ?? "📄"}</span>
                <ChevronRight className="mt-0.5 h-4 w-4 text-slate-500" />
              </div>
              <p className="mt-2 text-sm font-semibold text-white line-clamp-2">{r.title}</p>
              <p className="mt-1 text-xs capitalize text-slate-400">{r.report_type}</p>
              <div className="mt-3 flex items-center gap-1.5 text-[11px] text-slate-500">
                <Clock className="h-3 w-3" />
                {r.created_at.slice(0, 10)}
                {r.model_used && (
                  <span className="ml-1 font-mono text-cyan-400/70">{r.model_used.slice(0, 20)}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {loadingDetail && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
        </div>
      )}
    </section>
  );
}
