"use client";

import { useEffect, useState } from "react";
import {
  runOneClickAnalysis,
  saveReport,
  type BusinessInsight,
  type WorkflowResult,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  Lightbulb,
  Loader2,
  Plus,
  Save,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  X,
  Settings2,
  FileText as FileIcon
} from "lucide-react";

export default function WorkflowsPage() {
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<{
    workflow_type: string;
    query: string;
    result: WorkflowResult;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // KPI Customization
  const [showKPIs, setShowKPIs] = useState(false);
  const [customKPIs, setCustomKPIs] = useState<string[]>([
    "Net Revenue",
    "Gross Margin %",
    "EBITDA",
    "Burn Rate"
  ]);
  const [newKPI, setNewKPI] = useState("");

  const handleAnalyze = async () => {
    if (!query.trim()) return;
    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);
    setSaved(false);

    try {
      const res = await runOneClickAnalysis({ query }, token ?? undefined);
      setAnalysisResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSave = async () => {
    if (!analysisResult) return;
    setIsSaving(true);
    try {
      await saveReport({
        report_type: analysisResult.workflow_type,
        title: `Analysis: ${analysisResult.query.slice(0, 30)}${analysisResult.query.length > 30 ? '...' : ''}`,
        data: analysisResult.result,
        model_used: analysisResult.result.model_used,
        provider: analysisResult.result.provider
      }, token ?? undefined);
      setSaved(true);
    } catch (e) {
      setError("Failed to save report.");
    } finally {
      setIsSaving(false);
    }
  };

  const addKPI = () => {
    if (newKPI.trim() && !customKPIs.includes(newKPI.trim())) {
      setCustomKPIs([...customKPIs, newKPI.trim()]);
      setNewKPI("");
    }
  };

  const removeKPI = (kpi: string) => {
    setCustomKPIs(customKPIs.filter(k => k !== kpi));
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-20">
      {/* Hero Section */}
      <div className="text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-white lg:text-5xl">
          Business <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">Intelligence</span>
        </h1>
        <p className="mt-4 text-lg text-slate-400">
          Ask complex questions about your business documents and get executive insights in seconds.
        </p>
      </div>

      {/* Main Search Bar */}
      <div className="relative group">
        <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-indigo-500 to-cyan-500 opacity-20 blur transition duration-1000 group-hover:opacity-40 group-hover:duration-200"></div>
        <div className="relative flex flex-col gap-4 rounded-3xl border border-white/10 bg-slate-900/80 p-4 backdrop-blur-2xl lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
              placeholder="What do you want to analyze? e.g. 'How is our revenue performing?'"
              className="w-full rounded-2xl border border-white/5 bg-slate-950/50 py-4 pl-12 pr-4 text-lg text-white placeholder-slate-500 focus:border-indigo-500/50 focus:outline-none"
            />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !query.trim()}
            className="flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 px-8 py-4 text-lg font-bold text-white shadow-xl transition hover:scale-[1.02] hover:brightness-110 disabled:opacity-50 disabled:hover:scale-100"
          >
            {isAnalyzing ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <Sparkles className="h-6 w-6" />
            )}
            Analyze Business
          </button>
        </div>
      </div>

      {/* Workflow Templates (Restored) */}
      {!analysisResult && !isAnalyzing && (
        <div className="grid gap-6 md:grid-cols-3">
          {[
            { id: "financial", name: "Financial Health", desc: "Detailed revenue/expense audit", icon: TrendingUp, color: "emerald" },
            { id: "consulting", name: "Strategic SWOT", desc: "Consulting-grade strategic analysis", icon: Lightbulb, color: "cyan" },
            { id: "report", name: "Executive Summary", desc: "High-level management report", icon: FileIcon, color: "indigo" }
          ].map(wf => (
            <button
              key={wf.id}
              onClick={() => { setQuery(`Run ${wf.id} analysis`); handleAnalyze(); }}
              className="group relative rounded-[2rem] border border-white/10 bg-white/5 p-6 text-left transition hover:border-indigo-500/50 hover:bg-indigo-500/5"
            >
              <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-${wf.color}-500/10 text-${wf.color}-400 group-hover:scale-110 transition`}>
                <wf.icon className="h-6 w-6" />
              </div>
              <h3 className="font-bold text-white">{wf.name}</h3>
              <p className="mt-1 text-xs text-slate-500">{wf.desc}</p>
              <ArrowRight className="absolute bottom-6 right-6 h-5 w-5 text-slate-700 transition group-hover:text-indigo-400 group-hover:translate-x-1" />
            </button>
          ))}
        </div>
      )}
      <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/5 backdrop-blur-md">
        <button 
          onClick={() => setShowKPIs(!showKPIs)}
          className="flex w-full items-center justify-between px-6 py-4 transition hover:bg-white/5"
        >
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-indigo-400" />
            <span className="text-sm font-bold text-white uppercase tracking-wider">Customize KPIs</span>
          </div>
          {showKPIs ? <ChevronUp className="h-5 w-5 text-slate-500" /> : <ChevronDown className="h-5 w-5 text-slate-500" />}
        </button>
        
        {showKPIs && (
          <div className="border-t border-white/5 p-6">
            <div className="flex flex-wrap gap-2">
              {customKPIs.map(kpi => (
                <span key={kpi} className="flex items-center gap-2 rounded-xl bg-indigo-500/10 px-3 py-1.5 text-sm text-indigo-200 border border-indigo-500/20">
                  {kpi}
                  <button onClick={() => removeKPI(kpi)} className="text-indigo-400 hover:text-white">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={newKPI}
                  onChange={(e) => setNewKPI(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addKPI()}
                  placeholder="Add KPI..."
                  className="rounded-xl border border-white/10 bg-slate-950/50 px-3 py-1 text-sm text-white focus:outline-none"
                />
                <button onClick={addKPI} className="rounded-xl bg-white/10 p-1.5 text-slate-300 hover:bg-white/20">
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>
            <button className="mt-4 text-[10px] font-bold text-indigo-400 uppercase tracking-widest hover:text-indigo-300">Save Preferences</button>
          </div>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <p className="text-sm text-red-200">{error}</p>
        </div>
      )}

      {/* Results Section */}
      {analysisResult && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 space-y-6">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle2 className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Analysis Complete</h2>
                <p className="text-xs text-slate-500">Based on your documents in {analysisResult.workflow_type} category</p>
              </div>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={handleSave}
                disabled={isSaving || saved}
                className={`flex items-center gap-2 rounded-2xl px-5 py-2.5 text-sm font-bold transition ${saved ? 'bg-emerald-500/20 text-emerald-400' : 'bg-white/10 text-white hover:bg-white/15'}`}
              >
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {saved ? "Report Saved" : "Save Report"}
              </button>
            </div>
          </div>

          {/* Insight Display */}
          <div className="grid gap-6">
            {/* Summary */}
            <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-500/10 via-slate-900 to-slate-900 p-8 shadow-2xl">
              <div className="mb-4 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-400" />
                <span className="text-xs font-bold uppercase tracking-widest text-indigo-400">Executive Summary</span>
              </div>
              <p className="text-xl font-medium leading-relaxed text-slate-100 lg:text-2xl">
                {analysisResult.result.business_insight?.summary || "No summary available."}
              </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              {/* Findings */}
              <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
                <div className="mb-4 flex items-center gap-2 text-cyan-400">
                  <TrendingUp className="h-5 w-5" />
                  <span className="text-xs font-bold uppercase tracking-widest">Key Findings</span>
                </div>
                <ul className="space-y-4">
                  {analysisResult.result.business_insight?.key_findings.map((f, i) => (
                    <li key={i} className="flex gap-3 text-sm text-slate-300">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-cyan-500/10 text-[10px] font-bold text-cyan-400">
                        {i + 1}
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Risks */}
              <div className="rounded-3xl border border-red-500/20 bg-red-500/5 p-6 backdrop-blur-md">
                <div className="mb-4 flex items-center gap-2 text-red-400">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="text-xs font-bold uppercase tracking-widest">Critical Risks</span>
                </div>
                <ul className="space-y-4">
                  {analysisResult.result.business_insight?.risks.map((r, i) => (
                    <li key={i} className="flex gap-3 text-sm text-red-200/80">
                      <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommendations */}
              <div className="rounded-3xl border border-indigo-500/20 bg-indigo-500/5 p-6 backdrop-blur-md">
                <div className="mb-4 flex items-center gap-2 text-indigo-400">
                  <Target className="h-5 w-5" />
                  <span className="text-xs font-bold uppercase tracking-widest">Next Actions</span>
                </div>
                <ul className="space-y-4">
                  {analysisResult.result.business_insight?.recommendations.map((r, i) => (
                    <li key={i} className="flex gap-3 text-sm text-indigo-200/80">
                      <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Supporting Details (Collapsible) */}
            <div className="overflow-hidden rounded-3xl border border-white/5 bg-slate-950/30">
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between p-6 transition hover:bg-white/5">
                  <div className="flex items-center gap-2">
                    <Lightbulb className="h-4 w-4 text-slate-500" />
                    <span className="text-sm font-bold text-slate-500 uppercase tracking-wider">Detailed Analysis Data</span>
                  </div>
                  <ChevronDown className="h-5 w-5 text-slate-500 transition group-open:rotate-180" />
                </summary>
                <div className="border-t border-white/5 p-6">
                  <pre className="max-h-96 overflow-y-auto text-[10px] text-slate-400 font-mono">
                    {JSON.stringify(analysisResult.result.result, null, 2)}
                  </pre>
                </div>
              </details>
            </div>
          </div>
        </div>
      )}

      {/* Analysis Placeholder */}
      {!analysisResult && !isAnalyzing && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-indigo-500/10">
            <BarChartIcon className="h-12 w-12 text-indigo-400 opacity-50" />
          </div>
          <p className="text-lg font-medium text-slate-400">Ready for Analysis</p>
          <p className="mt-2 max-w-xs text-sm text-slate-600">
            Enter a query above to start extracting intelligence from your documents.
          </p>
        </div>
      )}
    </div>
  );
}

function BarChartIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" x2="12" y1="20" y2="10" />
      <line x1="18" x2="18" y1="20" y2="4" />
      <line x1="6" x2="6" y1="20" y2="16" />
    </svg>
  );
}
