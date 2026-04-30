"use client";

import { useEffect, useRef, useState } from "react";
import {
  listWorkflows, runWorkflow, saveReport, classifyWorkflow, runOneClickAnalysis,
  type WorkflowMeta, type BusinessInsight, type UnifiedAnalysis,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import {
  AlertTriangle, ArrowRight, BarChart2, CheckCircle, ChevronRight,
  Clock, Download, Lightbulb, Loader2, Play, Save, Search,
  Sparkles, Target, TrendingUp, Zap,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────
type WorkflowRun = {
  workflow: string;
  steps: string[];
  result: Record<string, unknown>;
  business_insight?: BusinessInsight;
  model_used: string;
  provider: string;
  duration_ms: number;
};

type HistoryEntry = WorkflowRun & { timestamp: string; saved_id?: string };

// ── Helpers ───────────────────────────────────────────────────────────────────
const WF_META: Record<string, { icon: string; label: string; color: string; accent: string }> = {
  financial:  { icon: "📊", label: "Financial Analysis",   color: "border-emerald-500/30 bg-emerald-500/8",  accent: "text-emerald-300" },
  consulting: { icon: "💡", label: "Consulting Analysis",  color: "border-indigo-500/30  bg-indigo-500/8",   accent: "text-indigo-300"  },
  report:     { icon: "📝", label: "Report Generation",    color: "border-amber-500/30   bg-amber-500/8",    accent: "text-amber-300"   },
};

function downloadJSON(data: unknown, name: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click();
}

// ── Executive Insight Card ────────────────────────────────────────────────────
function InsightCard({ insight, workflowType }: { insight: BusinessInsight; workflowType: string }) {
  const { accent } = WF_META[workflowType] ?? { accent: "text-cyan-300" };
  return (
    <div className="space-y-4">
      {/* Summary — the "so what" */}
      <div className="rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/10 to-indigo-500/5 p-5">
        <div className="mb-2 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-cyan-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-cyan-300">Executive Summary</span>
        </div>
        <p className="text-sm leading-relaxed text-white">{insight.summary}</p>
      </div>

      {/* 3 columns: findings / risks / recommendations */}
      <div className="grid gap-3 md:grid-cols-3">
        {/* Key Findings */}
        <div className="rounded-xl border border-white/10 bg-white/4 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <TrendingUp className={`h-3.5 w-3.5 ${accent}`} />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">Key Findings</span>
          </div>
          <ul className="space-y-2">
            {insight.key_findings.map((f, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-slate-200">
                <span className={`mt-0.5 shrink-0 text-[10px] font-bold ${accent}`}>{i + 1}.</span>
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Risks */}
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-red-300">Risks</span>
          </div>
          <ul className="space-y-2">
            {insight.risks.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-red-200">
                <span className="mt-0.5 shrink-0">⚠</span>
                {r}
              </li>
            ))}
          </ul>
        </div>

        {/* Recommendations */}
        <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5 text-indigo-400" />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-indigo-300">Actions</span>
          </div>
          <ul className="space-y-2">
            {insight.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-indigo-200">
                <ArrowRight className="mt-0.5 h-3 w-3 shrink-0" />
                {r}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ── Supporting data section (collapsible) ─────────────────────────────────────
function SupportingData({ result, workflowType }: { result: Record<string, unknown>; workflowType: string }) {
  const [open, setOpen] = useState(false);

  if (workflowType === "financial") {
    const rev = (result.revenue as Record<string, number>) || {};
    const exp = (result.expenses as Record<string, number>) || {};
    const tot = (result.totals as Record<string, number>) || {};
    return (
      <div>
        <button type="button" onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition">
          <ChevronRight className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-90" : ""}`} />
          Supporting Financial Data
        </button>
        {open && (
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
              <p className="mb-1.5 text-[10px] font-semibold uppercase text-slate-400">Revenue</p>
              {Object.entries(rev).map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs py-0.5">
                  <span className="capitalize text-slate-300">{k.replace(/_/g," ")}</span>
                  <span className="font-mono text-emerald-300">{(v as number).toLocaleString()}</span>
                </div>
              ))}
            </div>
            <div className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
              <p className="mb-1.5 text-[10px] font-semibold uppercase text-slate-400">Expenses</p>
              {Object.entries(exp).map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs py-0.5">
                  <span className="capitalize text-slate-300">{k.replace(/_/g," ")}</span>
                  <span className="font-mono text-red-300">{(v as number).toLocaleString()}</span>
                </div>
              ))}
            </div>
            <div className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
              <p className="mb-1.5 text-[10px] font-semibold uppercase text-slate-400">Totals</p>
              {Object.entries(tot).map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs py-0.5">
                  <span className="capitalize text-slate-300">{k.replace(/_/g," ")}</span>
                  <span className="font-mono text-cyan-300">{typeof v === "number" ? v.toLocaleString() : String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (workflowType === "consulting") {
    return (
      <div>
        <button type="button" onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition">
          <ChevronRight className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-90" : ""}`} />
          Full SWOT Detail
        </button>
        {open && (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {["strengths","weaknesses","opportunities","threats"].map((key) => {
              const items = (result[key] as string[]) || [];
              const colors: Record<string, string> = { strengths:"text-emerald-200", weaknesses:"text-red-200", opportunities:"text-cyan-200", threats:"text-amber-200" };
              return (
                <div key={key} className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
                  <p className="mb-1.5 text-[10px] font-semibold uppercase text-slate-400 capitalize">{key}</p>
                  {items.map((item, i) => (
                    <p key={i} className={`text-xs py-0.5 ${colors[key]}`}>• {item}</p>
                  ))}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // report
  const metrics = (result.key_metrics as Record<string, string>) || {};
  return (
    <div>
      <button type="button" onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition">
        <ChevronRight className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-90" : ""}`} />
        Key Metrics
      </button>
      {open && (
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(metrics).map(([k, v]) => (
            <span key={k} className="rounded-lg border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-xs text-cyan-200">
              <span className="font-semibold capitalize">{k.replace(/_/g," ")}:</span> {v}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Single workflow result panel ──────────────────────────────────────────────
function WorkflowResultPanel({
  run, onSave, isSaving, savedId,
}: {
  run: WorkflowRun;
  onSave: () => void;
  isSaving: boolean;
  savedId?: string;
}) {
  const meta = WF_META[run.workflow] ?? { icon: "⚙️", label: run.workflow, color: "border-white/10 bg-white/5", accent: "text-white" };

  return (
    <div className={`rounded-2xl border p-5 space-y-4 ${meta.color}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{meta.icon}</span>
          <div>
            <h3 className="text-sm font-semibold text-white">{meta.label}</h3>
            <div className="flex items-center gap-2 text-[10px] text-slate-400">
              <Clock className="h-3 w-3" />{run.duration_ms}ms
              <span className="font-mono text-cyan-300">{run.model_used}</span>
              <span>{run.provider}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-1.5">
          <button type="button" onClick={() => downloadJSON(run, `${run.workflow}-result.json`)}
            className="flex items-center gap-1 rounded-lg border border-white/15 bg-white/5 px-2 py-1 text-[11px] text-slate-200 hover:bg-white/10">
            <Download className="h-3 w-3" /> JSON
          </button>
          <button type="button" disabled={isSaving || !!savedId} onClick={onSave}
            className="flex items-center gap-1 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2 py-1 text-[11px] text-indigo-200 hover:bg-indigo-500/20 disabled:opacity-50">
            {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
            {savedId ? "Saved ✓" : "Save"}
          </button>
        </div>
      </div>

      {/* Business Insight — primary display */}
      {run.business_insight?.summary ? (
        <InsightCard insight={run.business_insight} workflowType={run.workflow} />
      ) : (
        <p className="text-xs text-slate-400">Insight generation unavailable. See supporting data below.</p>
      )}

      {/* Supporting data — collapsed by default */}
      <SupportingData result={run.result} workflowType={run.workflow} />
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function WorkflowsPage() {
  const { token } = useAuth();
  const [workflows, setWorkflows] = useState<WorkflowMeta[]>([]);
  const [selected, setSelected] = useState<string>("financial");
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<WorkflowRun | null>(null);
  const [unifiedResult, setUnifiedResult] = useState<UnifiedAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // NL query
  const [nlQuery, setNlQuery] = useState("");
  const [classifying, setClassifying] = useState(false);

  // Mode: "single" | "unified"
  const [mode, setMode] = useState<"single" | "unified">("single");

  useEffect(() => {
    listWorkflows(token ?? undefined)
      .then((r) => setWorkflows(r.workflows))
      .catch(() => {});
  }, [token]);

  // NL → auto-select workflow
  async function handleNLAnalyze() {
    if (!nlQuery.trim()) return;
    setClassifying(true);
    try {
      const { workflow } = await classifyWorkflow(nlQuery, token ?? undefined);
      setSelected(workflow);
      setMode("single");
    } finally {
      setClassifying(false);
    }
    await handleRun(selected);
  }

  async function handleRun(wfOverride?: string) {
    const wf = wfOverride || selected;
    setIsRunning(true);
    setError(null);
    setRunResult(null);
    setUnifiedResult(null);
    setSavedId(null);
    try {
      const res = await runWorkflow(
        { workflow: wf, input: {}, provider: "openai", model: "auto" },
        token ?? undefined
      );
      setRunResult(res as WorkflowRun);
      // Auto-save
      autoSave(res as WorkflowRun);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow failed.");
    } finally {
      setIsRunning(false);
    }
  }

  async function handleUnifiedAnalyze() {
    setIsRunning(true);
    setError(null);
    setRunResult(null);
    setUnifiedResult(null);
    setSavedId(null);
    try {
      const res = await runOneClickAnalysis(
        { provider: "openai", model: "auto" },
        token ?? undefined
      );
      setUnifiedResult(res);
      // Auto-save all 3
      for (const [wf, run] of Object.entries(res.workflows)) {
        autoSave(run as WorkflowRun, wf);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setIsRunning(false);
    }
  }

  function autoSave(run: WorkflowRun, wfOverride?: string) {
    const wf = wfOverride || run.workflow;
    const entry: HistoryEntry = {
      ...run,
      workflow: wf,
      timestamp: new Date().toISOString(),
    };
    setHistory((prev) => [entry, ...prev.slice(0, 9)]);
    // Persist to DB (fire and forget)
    saveReport({
      report_type: wf,
      title: `${WF_META[wf]?.label ?? wf} — ${new Date().toLocaleDateString()}`,
      data: { result: run.result, business_insight: run.business_insight },
      model_used: run.model_used,
      provider: run.provider,
    }, token ?? undefined).then((r) => {
      entry.saved_id = r.id;
    }).catch(() => {});
  }

  async function handleManualSave() {
    if (!runResult) return;
    setIsSaving(true);
    try {
      const r = await saveReport({
        report_type: runResult.workflow,
        title: `${WF_META[runResult.workflow]?.label ?? runResult.workflow} — ${new Date().toLocaleDateString()}`,
        data: { result: runResult.result, business_insight: runResult.business_insight },
        model_used: runResult.model_used,
        provider: runResult.provider,
      }, token ?? undefined);
      setSavedId(r.id);
    } finally {
      setIsSaving(false);
    }
  }

  const selectedMeta = WF_META[selected];

  return (
    <section className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-white">Business Intelligence Workflows</h2>
        <p className="mt-1 text-sm text-slate-400">
          AI-powered analysis that answers <span className="text-white font-medium">what happened</span>,{" "}
          <span className="text-white font-medium">why it matters</span>, and{" "}
          <span className="text-white font-medium">what to do next</span>.
        </p>
      </div>

      {/* NL query bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={nlQuery}
            onChange={(e) => setNlQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleNLAnalyze()}
            placeholder="What do you want to analyze? e.g. 'Show me our revenue and profit margins'"
            className="w-full rounded-xl border border-white/20 bg-slate-950/70 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-cyan-400/50 focus:outline-none"
          />
        </div>
        <button
          type="button"
          disabled={!nlQuery.trim() || classifying || isRunning}
          onClick={handleNLAnalyze}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-50"
        >
          {classifying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lightbulb className="h-4 w-4" />}
          Analyze
        </button>
      </div>

      {/* Mode tabs + one-click */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-xl border border-white/10 bg-white/5 p-1">
          {(["single", "unified"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                mode === m ? "bg-white/15 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              {m === "single" ? "Single Workflow" : "Full Analysis"}
            </button>
          ))}
        </div>

        {mode === "unified" && (
          <button
            type="button"
            disabled={isRunning}
            onClick={handleUnifiedAnalyze}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 px-5 py-2 text-sm font-semibold text-white shadow-lg hover:brightness-110 disabled:opacity-50"
          >
            {isRunning
              ? <><Loader2 className="h-4 w-4 animate-spin" /> Running all workflows…</>
              : <><Zap className="h-4 w-4" /> Analyze Business (One Click)</>
            }
          </button>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-4">
        {/* Left: workflow selector (only in single mode) */}
        {mode === "single" && (
          <div className="space-y-3 lg:col-span-1">
            <article className="rounded-2xl border border-white/15 bg-white/5 p-4">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Workflow</h3>
              <div className="space-y-1.5">
                {workflows.map((wf) => {
                  const m = WF_META[wf.name];
                  return (
                    <button
                      key={wf.name}
                      type="button"
                      onClick={() => { setSelected(wf.name); setRunResult(null); setError(null); }}
                      className={`w-full rounded-xl border p-3 text-left transition ${
                        selected === wf.name
                          ? "border-cyan-400/40 bg-cyan-500/10"
                          : "border-white/10 bg-white/3 hover:bg-white/8"
                      }`}
                    >
                      <p className="flex items-center gap-2 text-sm font-semibold text-white">
                        <span>{m?.icon ?? "⚙"}</span>{wf.label}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-400 leading-relaxed">{wf.description}</p>
                    </button>
                  );
                })}
              </div>
            </article>

            <button
              type="button"
              disabled={isRunning}
              onClick={() => handleRun()}
              className={`w-full rounded-xl bg-gradient-to-r py-2.5 text-sm font-semibold text-white shadow hover:brightness-110 disabled:opacity-50 ${
                selected === "financial" ? "from-emerald-500 to-cyan-500" :
                selected === "consulting" ? "from-indigo-500 to-purple-500" :
                "from-amber-500 to-orange-500"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                {isRunning ? <><Loader2 className="h-4 w-4 animate-spin" /> Running…</> : <><Play className="h-4 w-4" /> Run {selectedMeta?.label}</>}
              </span>
            </button>

            {/* History */}
            {history.length > 0 && (
              <article className="rounded-2xl border border-white/10 bg-white/3 p-3">
                <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Recent Analyses</h4>
                <div className="space-y-1.5">
                  {history.slice(0, 6).map((h, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => { setRunResult(h); setUnifiedResult(null); setError(null); }}
                      className="w-full rounded-lg border border-white/8 bg-white/4 p-2 text-left hover:bg-white/8 transition"
                    >
                      <p className="text-xs text-white">{WF_META[h.workflow]?.icon} {WF_META[h.workflow]?.label ?? h.workflow}</p>
                      <p className="text-[10px] text-slate-500">{h.timestamp.slice(0, 19).replace("T", " ")}</p>
                    </button>
                  ))}
                </div>
              </article>
            )}
          </div>
        )}

        {/* Right: results panel */}
        <div className={mode === "unified" ? "lg:col-span-4" : "lg:col-span-3"}>
          {/* Empty state */}
          {!runResult && !unifiedResult && !isRunning && !error && (
            <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/2 p-8 text-center">
              <BarChart2 className="mb-3 h-12 w-12 text-slate-600" />
              <p className="text-sm font-semibold text-slate-300">Ready to analyse your business</p>
              <p className="mt-1.5 max-w-xs text-xs text-slate-500">
                Ask a question in the search bar above, or select a workflow and click Run.
                The AI will retrieve your indexed documents automatically.
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {["How is our revenue performing?", "What are our strategic risks?", "Generate a performance report"].map((q) => (
                  <button key={q} type="button"
                    onClick={() => { setNlQuery(q); }}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300 hover:bg-white/10 transition">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Loading */}
          {isRunning && (
            <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-8 text-center">
              <Loader2 className="mb-3 h-10 w-10 animate-spin text-cyan-400" />
              <p className="text-sm font-semibold text-white">
                {mode === "unified" ? "Running full business analysis…" : `Running ${selectedMeta?.label}…`}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Retrieving documents → Analysing → Generating insights
              </p>
            </div>
          )}

          {/* Error */}
          {error && !isRunning && (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5">
              <p className="text-sm font-semibold text-red-300">Analysis Failed</p>
              <p className="mt-1 text-xs text-red-200">{error}</p>
            </div>
          )}

          {/* Single workflow result */}
          {runResult && !isRunning && (
            <WorkflowResultPanel
              run={runResult}
              onSave={handleManualSave}
              isSaving={isSaving}
              savedId={savedId ?? undefined}
            />
          )}

          {/* Unified analysis result */}
          {unifiedResult && !isRunning && (
            <div className="space-y-4">
              {/* Executive overview strip */}
              <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-purple-500/5 p-5">
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-indigo-400" />
                  <h3 className="text-base font-semibold text-white">Full Business Analysis — Executive Overview</h3>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {Object.entries(unifiedResult.summary).map(([wf, summary]) => (
                    summary ? (
                      <div key={wf} className={`rounded-xl border p-3 ${WF_META[wf]?.color ?? "border-white/10"}`}>
                        <p className="mb-1 text-xs font-semibold text-white">{WF_META[wf]?.icon} {WF_META[wf]?.label}</p>
                        <p className="text-xs leading-relaxed text-slate-300">{summary}</p>
                      </div>
                    ) : null
                  ))}
                </div>
              </div>

              {/* Each workflow detail */}
              {Object.entries(unifiedResult.workflows).map(([wf, run]) => (
                <WorkflowResultPanel
                  key={wf}
                  run={run as WorkflowRun}
                  onSave={() => {}}
                  isSaving={false}
                  savedId="auto"
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
