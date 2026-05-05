"use client";

import { useEffect, useState } from "react";
import {
  listSavedReports,
  getSavedReport,
  deleteSavedReport,
  exportSavedReport,
  type SavedReportMeta,
  type SavedReportFull,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import {
  BookMarked,
  Calendar,
  ChevronRight,
  Clock,
  Download,
  FileJson,
  FileSpreadsheet,
  Loader2,
  MoreVertical,
  Search,
  Trash2,
  X,
  Eye,
  FileText,
  BarChart3,
  Lightbulb,
  AlertCircle
} from "lucide-react";

const TYPE_CONFIG: Record<string, { icon: any; color: string; bg: string }> = {
  financial: { icon: BarChart3, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  consulting: { icon: Lightbulb, color: "text-indigo-400", bg: "bg-indigo-500/10" },
  report: { icon: FileText, color: "text-amber-400", bg: "bg-amber-500/10" },
  debt: { icon: AlertCircle, color: "text-red-400", bg: "bg-red-500/10" },
};

export default function ReportsPage() {
  const { token } = useAuth();
  const [reports, setReports] = useState<SavedReportMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedReport, setSelectedReport] = useState<SavedReportFull | null>(null);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const r = await listSavedReports(token ?? undefined);
      setReports(r.reports);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [token]);

  const filteredReports = reports.filter(r => 
    r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.report_type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this report?")) return;
    setIsDeleting(id);
    try {
      await deleteSavedReport(id, token ?? undefined);
      await fetchReports();
    } catch (e) {
      alert("Failed to delete report.");
    } finally {
      setIsDeleting(null);
    }
  };

  const handleDownload = async (id: string, format: "json" | "csv", e: React.MouseEvent) => {
    e.stopPropagation();
    if (format === "csv") {
      const url = exportSavedReport(id, "csv", token ?? undefined) as string;
      window.open(url, "_blank");
    } else {
      try {
        const data = await exportSavedReport(id, "json", token ?? undefined) as Record<string, unknown>;
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `report-${id.slice(0, 8)}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        alert("Failed to export JSON.");
      }
    }
  };

  const openReport = async (id: string) => {
    setViewingId(id);
    try {
      const r = await getSavedReport(id, token ?? undefined);
      setSelectedReport(r);
    } catch (e) {
      alert("Failed to load report details.");
    } finally {
      setViewingId(null);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Report Vault</h1>
          <p className="mt-2 text-slate-400">
            Access, view, and export all your saved business intelligence reports.
          </p>
        </div>
        
        <div className="relative w-full lg:w-96">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search reports..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/50 py-2.5 pl-11 pr-4 text-sm text-white placeholder-slate-500 focus:border-indigo-500/50 focus:outline-none"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          <p className="text-sm text-slate-500 font-medium">Loading your reports...</p>
        </div>
      ) : filteredReports.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-white/10 bg-white/2 py-24 text-center">
          <BookMarked className="mb-4 h-12 w-12 text-slate-700" />
          <p className="text-lg font-medium text-slate-400">No reports found</p>
          <p className="mt-1 text-sm text-slate-600">Run a workflow and save the results to see them here.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredReports.map((report) => {
            const config = TYPE_CONFIG[report.report_type] || { icon: FileText, color: "text-slate-400", bg: "bg-slate-500/10" };
            const Icon = config.icon;
            
            return (
              <div 
                key={report.id}
                onClick={() => openReport(report.id)}
                className="group relative cursor-pointer overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-5 transition hover:border-white/20 hover:bg-white/10"
              >
                <div className="flex items-start justify-between">
                  <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${config.bg} ${config.color}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div className="flex gap-1 opacity-0 transition group-hover:opacity-100">
                    <button 
                      onClick={(e) => handleDelete(report.id, e)}
                      className="rounded-lg p-2 text-slate-400 hover:bg-red-500/10 hover:text-red-400"
                    >
                      {isDeleting === report.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div className="mt-6">
                  <h3 className="line-clamp-2 font-bold text-white transition group-hover:text-indigo-400">{report.title}</h3>
                  <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">{report.report_type}</p>
                </div>

                <div className="mt-6 flex items-center justify-between border-t border-white/5 pt-4">
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                    <Calendar className="h-3 w-3" />
                    {new Date(report.created_at).toLocaleDateString()}
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={(e) => handleDownload(report.id, "csv", e)}
                      className="rounded-lg bg-white/5 p-2 text-slate-400 hover:bg-white/10 hover:text-white"
                      title="Download CSV"
                    >
                      <FileSpreadsheet className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={(e) => handleDownload(report.id, "json", e)}
                      className="rounded-lg bg-white/5 p-2 text-slate-400 hover:bg-white/10 hover:text-white"
                      title="Download JSON"
                    >
                      <FileJson className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {viewingId === report.id && (
                  <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm">
                    <Loader2 className="h-6 w-6 animate-spin text-white" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md animate-in fade-in duration-300">
          <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-[2.5rem] border border-white/10 bg-slate-900 shadow-2xl flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/5 px-8 py-6 bg-white/5">
              <div className="flex items-center gap-4">
                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${TYPE_CONFIG[selectedReport.report_type]?.bg} ${TYPE_CONFIG[selectedReport.report_type]?.color}`}>
                  {(() => {
                    const Icon = TYPE_CONFIG[selectedReport.report_type]?.icon || FileText;
                    return <Icon className="h-6 w-6" />;
                  })()}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">{selectedReport.title}</h2>
                  <p className="text-xs text-slate-500 uppercase tracking-widest">{selectedReport.report_type} Report · {new Date(selectedReport.created_at).toLocaleString()}</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedReport(null)}
                className="rounded-full bg-white/5 p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-8 space-y-8">
              {selectedReport.data?.business_insight ? (
                <div className="space-y-6">
                  <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-500/10 to-transparent p-8">
                    <h4 className="mb-4 text-xs font-bold uppercase tracking-widest text-indigo-400">Executive Summary</h4>
                    <p className="text-xl font-medium leading-relaxed text-white">{(selectedReport.data.business_insight as any).summary}</p>
                  </div>
                  
                  <div className="grid gap-6 lg:grid-cols-3">
                    <div className="rounded-2xl bg-white/5 p-5">
                      <h5 className="mb-3 text-[10px] font-bold uppercase tracking-widest text-emerald-400">Findings</h5>
                      <ul className="space-y-3 text-sm text-slate-300">
                        {(selectedReport.data.business_insight as any).key_findings?.map((f: string, i: number) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-emerald-500 font-bold">•</span>
                            {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-2xl bg-white/5 p-5">
                      <h5 className="mb-3 text-[10px] font-bold uppercase tracking-widest text-red-400">Risks</h5>
                      <ul className="space-y-3 text-sm text-slate-300">
                        {(selectedReport.data.business_insight as any).risks?.map((r: string, i: number) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-red-500 font-bold">•</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-2xl bg-white/5 p-5">
                      <h5 className="mb-3 text-[10px] font-bold uppercase tracking-widest text-indigo-400">Actions</h5>
                      <ul className="space-y-3 text-sm text-slate-300">
                        {(selectedReport.data.business_insight as any).recommendations?.map((r: string, i: number) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-indigo-500 font-bold">•</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl bg-white/5 p-8 text-center">
                  <p className="text-slate-400">Full analysis insight not available for this report version.</p>
                </div>
              )}

              <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-widest text-slate-500">Raw Source Data</h4>
                <div className="rounded-2xl bg-slate-950 p-4 font-mono text-[10px] text-slate-500">
                  <pre className="max-h-64 overflow-y-auto">
                    {JSON.stringify(selectedReport.data?.result || selectedReport.data, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-white/5 px-8 py-6 bg-white/5">
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <p>Model: <span className="text-indigo-400 font-mono">{selectedReport.model_used || "auto"}</span></p>
                <p>Provider: <span className="text-cyan-400 font-mono">{selectedReport.provider || "auto"}</span></p>
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={(e) => handleDownload(selectedReport.id, "csv", e)}
                  className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-bold text-white transition hover:bg-white/10"
                >
                  <FileSpreadsheet className="h-4 w-4" /> CSV
                </button>
                <button 
                  onClick={(e) => handleDownload(selectedReport.id, "json", e)}
                  className="flex items-center gap-2 rounded-xl bg-indigo-500 px-4 py-2 text-sm font-bold text-white transition hover:brightness-110"
                >
                  <FileJson className="h-4 w-4" /> JSON
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
