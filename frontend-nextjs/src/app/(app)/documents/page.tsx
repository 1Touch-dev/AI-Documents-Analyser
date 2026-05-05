"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import {
  deleteDocument,
  getDocumentStatus,
  getBatchStatus,
  listDocuments,
  type BatchStatusResponse,
  type DocumentStatusResponse,
  type DocumentItem,
  type UploadBatchResponse,
  uploadBatch,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { 
  FileText, 
  Search, 
  Filter, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  ChevronDown,
  ChevronUp,
  FileCode,
  FilePieChart,
  FileBox,
  UploadCloud,
  Loader2,
  LayoutGrid,
  List
} from "lucide-react";

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

const CATEGORIES = [
  "Financial",
  "F&B",
  "Ticketing",
  "Retail",
  "Player Sales",
  "Sponsors",
  "Legal",
  "HR",
  "Operations",
  "Others"
];

export default function DocumentsPage() {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadCategory, setUploadCategory] = useState("Financial");
  const [uploadSummary, setUploadSummary] = useState<UploadBatchResponse | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // UI State
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string | "All">("All");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    "Financial": true,
    "F&B": true,
    "Ticketing": true,
    "Others": true
  });

  const refreshDocuments = async (showRefreshState = false) => {
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
  };

  useEffect(() => {
    refreshDocuments();
  }, [token]);

  // Grouping logic
  const groupedDocs = useMemo(() => {
    let filtered = documents;
    if (searchQuery) {
      filtered = filtered.filter(d => d.title.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    if (filterCategory !== "All") {
      filtered = filtered.filter(d => d.category === filterCategory);
    }

    const groups: Record<string, DocumentItem[]> = {};
    filtered.forEach(doc => {
      const cat = doc.category || "Others";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(doc);
    });

    return groups;
  }, [documents, searchQuery, filterCategory]);

  const metrics = useMemo(() => {
    const ready = documents.filter((d) => normalizeStatus(d.status) === "ready").length;
    const processing = documents.filter((d) => normalizeStatus(d.status) === "processing").length;
    const totalSizeMb = documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0) / (1024 * 1024);
    return { total: documents.length, ready, processing, totalSizeMb };
  }, [documents]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFiles(Array.from(event.target.files || []));
  };

  const onUpload = async () => {
    if (!selectedFiles.length) return;
    setIsUploading(true);
    try {
      const result = await uploadBatch(selectedFiles, uploadCategory, token ?? undefined);
      setUploadSummary(result);
      setSelectedFiles([]);
      refreshDocuments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const onDelete = async (documentId: string) => {
    try {
      await deleteDocument(documentId, token ?? undefined);
      await refreshDocuments(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    }
  };

  const toggleCategory = (cat: string) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  const getStatusIcon = (status?: string) => {
    const normalized = normalizeStatus(status);
    if (normalized === "ready") return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    if (normalized === "processing") return <Loader2 className="h-4 w-4 animate-spin text-amber-400" />;
    return <AlertCircle className="h-4 w-4 text-red-400" />;
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-12">
      {/* Header & Metrics */}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Document Management</h1>
          <p className="mt-2 text-slate-400">
            Organize, classify, and manage your business documents for analysis.
          </p>
        </div>
        
        <div className="flex gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-3 backdrop-blur-md">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Total Files</p>
            <p className="text-xl font-bold text-white">{metrics.total}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-3 backdrop-blur-md">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Ready</p>
            <p className="text-xl font-bold text-emerald-400">{metrics.ready}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-3 backdrop-blur-md">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Processing</p>
            <p className="text-xl font-bold text-amber-400">{metrics.processing}</p>
          </div>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-slate-900/40 p-4 backdrop-blur-xl lg:flex-row lg:items-center">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/50 py-2.5 pl-11 pr-4 text-sm text-white placeholder-slate-500 focus:border-indigo-500/50 focus:outline-none"
          />
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2 px-2">
          <Filter className="h-4 w-4 text-slate-500" />
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-slate-300 focus:outline-none"
          >
            <option value="All">All Categories</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* View Switcher */}
        <div className="flex gap-1 rounded-xl bg-slate-950/50 p-1">
          <button 
            onClick={() => setViewMode("grid")}
            className={`rounded-lg p-2 transition ${viewMode === "grid" ? "bg-white/15 text-white" : "text-slate-500 hover:text-slate-300"}`}
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button 
            onClick={() => setViewMode("list")}
            className={`rounded-lg p-2 transition ${viewMode === "list" ? "bg-white/15 text-white" : "text-slate-500 hover:text-slate-300"}`}
          >
            <List className="h-4 w-4" />
          </button>
        </div>

        {/* Refresh */}
        <button
          onClick={() => refreshDocuments(true)}
          disabled={isRefreshing}
          className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* Main Content: Grouped List */}
        <div className="space-y-6">
          {Object.keys(groupedDocs).length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-white/10 bg-white/2 py-24 text-center">
              <FileBox className="mb-4 h-12 w-12 text-slate-700" />
              <p className="text-lg font-medium text-slate-400">No documents found</p>
              <p className="mt-1 text-sm text-slate-600">Try adjusting your filters or upload new files.</p>
            </div>
          ) : (
            Object.entries(groupedDocs).sort().map(([cat, docs]) => (
              <div key={cat} className="overflow-hidden rounded-3xl border border-white/10 bg-white/5 backdrop-blur-md">
                <button
                  onClick={() => toggleCategory(cat)}
                  className="flex w-full items-center justify-between border-b border-white/5 bg-white/5 px-6 py-4 transition hover:bg-white/10"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400">
                      <FilePieChart className="h-5 w-5" />
                    </div>
                    <div className="text-left">
                      <h3 className="font-semibold text-white">{cat}</h3>
                      <p className="text-xs text-slate-500">{docs.length} file{docs.length !== 1 ? 's' : ''}</p>
                    </div>
                  </div>
                  {expandedCategories[cat] ? <ChevronUp className="h-5 w-5 text-slate-500" /> : <ChevronDown className="h-5 w-5 text-slate-500" />}
                </button>

                {expandedCategories[cat] && (
                  <div className={`p-4 ${viewMode === "grid" ? "grid gap-4 sm:grid-cols-2" : "space-y-2"}`}>
                    {docs.map(doc => (
                      <div 
                        key={doc.id}
                        className={`group relative rounded-2xl border border-white/5 bg-slate-900/40 p-4 transition hover:border-white/20 hover:bg-slate-900/60 ${viewMode === "list" ? "flex items-center gap-4" : ""}`}
                      >
                        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl transition group-hover:scale-110 ${doc.file_type.includes('xls') ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-500/10 text-indigo-400'}`}>
                          {doc.file_type.includes('xls') ? <FileCode className="h-6 w-6" /> : <FileText className="h-6 w-6" />}
                        </div>
                        
                        <div className="min-w-0 flex-1">
                          <h4 className="truncate text-sm font-medium text-slate-100">{doc.title}</h4>
                          <div className="mt-1 flex items-center gap-3 text-[10px] text-slate-500">
                            <span className="uppercase">{doc.file_type}</span>
                            <span>{((doc.file_size || 0) / 1024).toFixed(1)} KB</span>
                            <div className="flex items-center gap-1">
                              {getStatusIcon(doc.status)}
                              <span className="capitalize">{normalizeStatus(doc.status)}</span>
                            </div>
                          </div>
                        </div>

                        <button 
                          onClick={() => onDelete(doc.id)}
                          className="ml-2 rounded-lg p-2 text-slate-600 transition hover:bg-red-500/10 hover:text-red-400"
                          title="Delete document"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Sidebar: Upload */}
        <div className="space-y-6">
          <div className="sticky top-24 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
            <h3 className="text-lg font-bold text-white">Import Documents</h3>
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">
              Upload PDF, Excel, or CSV files. Our AI will automatically categorize them for you.
            </p>

            <div className="mt-6 space-y-4">
              <div className="relative">
                <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Category (Optional)</label>
                <select
                  value={uploadCategory}
                  onChange={(e) => setUploadCategory(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-950/50 px-4 py-2.5 text-sm text-white focus:outline-none"
                >
                  <option value="Auto">Auto-Detect (AI)</option>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div className="group relative mt-2">
                <input
                  type="file"
                  multiple
                  onChange={onFileChange}
                  className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                />
                <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-white/10 bg-slate-950/30 py-8 transition group-hover:border-indigo-500/40 group-hover:bg-indigo-500/5">
                  <UploadCloud className="mb-2 h-8 w-8 text-slate-600 group-hover:text-indigo-400" />
                  <p className="text-xs font-medium text-slate-400 group-hover:text-slate-200">
                    {selectedFiles.length ? `${selectedFiles.length} files selected` : "Drop files here or click"}
                  </p>
                </div>
              </div>

              <button
                onClick={onUpload}
                disabled={isUploading || selectedFiles.length === 0}
                className="w-full rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 transition hover:scale-[1.02] hover:brightness-110 disabled:opacity-50 disabled:hover:scale-100"
              >
                {isUploading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Processing...
                  </span>
                ) : "Upload & Analyze"}
              </button>
            </div>

            {uploadSummary && (
              <div className="mt-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <p className="text-xs font-bold text-emerald-400 uppercase">Success</p>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">
                  {uploadSummary.accepted} documents are being indexed. This may take a minute.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
