"use client";

import { useState, useEffect } from "react";
import { 
  FileSpreadsheet, 
  Sparkles, 
  Send, 
  Download, 
  Settings2, 
  AlertCircle, 
  CheckCircle2, 
  Loader2,
  FileText,
  Table as TableIcon,
  Code
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  generateReport, 
  getModels,
  type ReportResponse 
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export default function ReportGenerationPage() {
  const { token } = useAuth();
  const [topic, setTopic] = useState("");
  const [query, setQuery] = useState("");
  const [reportType, setReportType] = useState("general");
  const [outputFormat, setOutputFormat] = useState<"markdown" | "table" | "json">("markdown");
  const [model, setModel] = useState("auto");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      getModels(token).then(res => setAvailableModels(res.models)).catch(console.error);
    }
  }, [token]);

  const handleGenerate = async () => {
    if (!topic.trim() || !query.trim()) return;
    setIsGenerating(true);
    setError(null);
    setResult(null);

    try {
      const res = await generateReport({
        topic,
        query,
        report_type: reportType,
        output_format: outputFormat,
        model: model !== "auto" ? model : undefined
      }, token ?? undefined);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report.");
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadReport = () => {
    if (!result) return;
    const blob = new Blob([result.report], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Report_${topic.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">Report Generation</h1>
        <p className="text-slate-400">Synthesize deep-dive reports across your entire document knowledge base.</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* Main Configuration */}
        <div className="space-y-6">
          <div className="rounded-[2.5rem] border border-white/10 bg-slate-900/40 p-8 backdrop-blur-xl shadow-2xl">
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Report Topic</label>
                <input 
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Q1 Financial Performance"
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-6 py-4 text-white placeholder-slate-600 focus:border-indigo-500/50 focus:outline-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Research Query</label>
                <textarea 
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={4}
                  placeholder="What specifically should the report cover? e.g. Analyze revenue growth, expense anomalies, and risk factors."
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-6 py-4 text-white placeholder-slate-600 focus:border-indigo-500/50 focus:outline-none resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Report Type</label>
                  <select 
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-slate-950/50 p-3 text-sm text-white focus:outline-none"
                  >
                    <option value="general">General Audit</option>
                    <option value="financial">Financial Analysis</option>
                    <option value="legal">Legal Review</option>
                    <option value="strategic">Strategic SWOT</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Output Format</label>
                  <div className="flex gap-1 rounded-xl bg-slate-950/50 p-1 border border-white/5">
                    <button 
                      onClick={() => setOutputFormat("markdown")}
                      className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-xs transition ${outputFormat === 'markdown' ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                      <FileText className="h-3 w-3" />
                      MD
                    </button>
                    <button 
                      onClick={() => setOutputFormat("table")}
                      className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-xs transition ${outputFormat === 'table' ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                      <TableIcon className="h-3 w-3" />
                      Table
                    </button>
                    <button 
                      onClick={() => setOutputFormat("json")}
                      className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-xs transition ${outputFormat === 'json' ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                      <Code className="h-3 w-3" />
                      JSON
                    </button>
                  </div>
                </div>
              </div>

              <button 
                onClick={handleGenerate}
                disabled={isGenerating || !topic.trim() || !query.trim()}
                className="w-full flex items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 py-4 text-lg font-bold text-white shadow-xl shadow-indigo-500/20 transition hover:scale-[1.02] hover:brightness-110 disabled:opacity-50 disabled:hover:scale-100"
              >
                {isGenerating ? <Loader2 className="h-6 w-6 animate-spin" /> : <Sparkles className="h-6 w-6" />}
                Generate Report
              </button>
            </div>
          </div>

          {/* Result Area */}
          {result && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 space-y-6">
              <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">Report Ready</h2>
                    <p className="text-xs text-slate-500">Generated using {result.model_used || 'AI Engine'}</p>
                  </div>
                </div>
                <button 
                  onClick={downloadReport}
                  className="flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm font-bold text-white transition hover:bg-white/10"
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
              </div>

              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-8 backdrop-blur-xl">
                <div className="prose prose-invert max-w-none prose-sm prose-headings:text-white prose-p:text-slate-300 prose-strong:text-indigo-400 prose-ul:text-slate-400">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {result.report}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4 flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <p className="text-sm text-red-200">{error}</p>
            </div>
          )}
        </div>

        {/* Sidebar: Settings */}
        <div className="space-y-6">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
            <div className="flex items-center gap-2 mb-6">
              <Settings2 className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Engine Settings</h3>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Model Choice</label>
                <select 
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-950/50 p-3 text-xs text-white focus:outline-none"
                >
                  <option value="auto">Auto-Select (Optimized)</option>
                  {availableModels.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <div className="rounded-2xl bg-indigo-500/5 border border-indigo-500/10 p-4">
                <p className="text-[10px] text-indigo-300 leading-relaxed">
                  <strong>Pro Tip:</strong> Use "Table" format for financial data and "Markdown" for executive summaries.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
