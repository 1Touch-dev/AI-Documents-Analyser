"use client";

import { useEffect, useState } from "react";
import { listWorkflows, runWorkflow, type WorkflowMeta } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { useAppPreferences } from "@/contexts/app-preferences-context";
import { CheckCircle, ChevronRight, Clock, Download, Loader2, Play, Save, Zap } from "lucide-react";
import { saveReport } from "@/lib/api";

// ── Workflow card metadata ────────────────────────────────────────────────────
const WORKFLOW_ICONS: Record<string, string> = {
  financial:  "📊",
  consulting: "💡",
  report:     "📝",
};

const WORKFLOW_COLORS: Record<string, string> = {
  financial:  "from-emerald-500 to-cyan-500",
  consulting: "from-indigo-500 to-purple-500",
  report:     "from-amber-500 to-orange-500",
};

// ── Helper: flatten nested result for table view ──────────────────────────────
function flattenResult(obj: unknown, prefix = ""): Array<{ key: string; value: string }> {
  if (typeof obj !== "object" || obj === null) {
    return [{ key: prefix, value: String(obj) }];
  }
  if (Array.isArray(obj)) {
    return obj.flatMap((v, i) => flattenResult(v, prefix ? `${prefix}[${i}]` : String(i)));
  }
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    flattenResult(v, prefix ? `${prefix}.${k}` : k)
  );
}

// ── Download result as JSON or CSV ────────────────────────────────────────────
function downloadJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function downloadCSV(rows: Array<{ key: string; value: string }>, filename: string) {
  const csv = ["field,value", ...rows.map((r) => `"${r.key}","${r.value.replace(/"/g, '""')}"`)]
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

// ── Structured result renderers ───────────────────────────────────────────────

function FinancialResult({ result }: { result: Record<string, unknown> }) {
  const rev = (result.revenue as Record<string, number>) || {};
  const exp = (result.expenses as Record<string, number>) || {};
  const tot = (result.totals as Record<string, number>) || {};
  const insights = (result.insights as string[]) || [];
  const risks = (result.risks as string[]) || [];
  const opps = (result.opportunities as string[]) || [];

  return (
    <div className="space-y-4">
      {/* Totals strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Total Revenue", value: tot.total_revenue, color: "text-emerald-300" },
          { label: "Total Expenses", value: tot.total_expenses, color: "text-red-300" },
          { label: "Net Profit", value: tot.net_profit, color: tot.net_profit >= 0 ? "text-emerald-300" : "text-red-300" },
          { label: "Margin %", value: `${tot.margin_pct ?? 0}%`, color: "text-cyan-300" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border border-white/10 bg-slate-900/60 p-3 text-center">
            <p className="text-[11px] text-slate-400">{label}</p>
            <p className={`mt-1 text-lg font-bold ${color}`}>
              {typeof value === "number" ? value.toLocaleString() : value}
            </p>
          </div>
        ))}
      </div>

      {/* Revenue + Expense tables side by side */}
      <div className="grid gap-3 md:grid-cols-2">
        {[
          { title: "Revenue Breakdown", data: rev, color: "text-emerald-300" },
          { title: "Expense Breakdown", data: exp, color: "text-red-300" },
        ].map(({ title, data, color }) => (
          <div key={title} className="rounded-xl border border-white/10 bg-slate-900/40 p-3">
            <h5 className="mb-2 text-xs font-semibold text-slate-200">{title}</h5>
            <table className="w-full text-xs">
              <tbody>
                {Object.entries(data).map(([k, v]) => (
                  <tr key={k} className="border-t border-white/5">
                    <td className="py-1.5 capitalize text-slate-300">{k.replace(/_/g, " ")}</td>
                    <td className={`py-1.5 text-right font-mono font-semibold ${color}`}>
                      {typeof v === "number" ? v.toLocaleString() : String(v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {/* Insights / Risks / Opportunities */}
      <div className="grid gap-3 md:grid-cols-3">
        {[
          { label: "Insights", items: insights, col: "text-cyan-200" },
          { label: "Risks", items: risks, col: "text-red-200" },
          { label: "Opportunities", items: opps, col: "text-emerald-200" },
        ].map(({ label, items, col }) => (
          <div key={label} className="rounded-xl border border-white/10 bg-slate-900/40 p-3">
            <h5 className="mb-2 text-xs font-semibold text-slate-200">{label}</h5>
            <ul className="space-y-1.5">
              {items.map((item, i) => (
                <li key={i} className={`text-xs leading-relaxed ${col}`}>• {item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConsultingResult({ result }: { result: Record<string, unknown> }) {
  const sections = [
    { key: "strengths",        label: "Strengths",        col: "border-emerald-500/30 bg-emerald-500/5", textCol: "text-emerald-200" },
    { key: "weaknesses",       label: "Weaknesses",       col: "border-red-500/30    bg-red-500/5",      textCol: "text-red-200"     },
    { key: "opportunities",    label: "Opportunities",    col: "border-cyan-500/30   bg-cyan-500/5",     textCol: "text-cyan-200"    },
    { key: "threats",          label: "Threats",          col: "border-amber-500/30  bg-amber-500/5",    textCol: "text-amber-200"   },
    { key: "strategic_actions",label: "Strategic Actions",col: "border-indigo-500/30 bg-indigo-500/5",   textCol: "text-indigo-200"  },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {sections.map(({ key, label, col, textCol }) => {
        const items = (result[key] as string[]) || [];
        return (
          <div key={key} className={`rounded-xl border p-4 ${col} ${key === "strategic_actions" ? "sm:col-span-2" : ""}`}>
            <h5 className="mb-2 text-xs font-semibold text-white">{label}</h5>
            <ul className="space-y-1.5">
              {items.map((item, i) => (
                <li key={i} className={`text-xs leading-relaxed ${textCol}`}>• {item}</li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

function ReportResult({ result }: { result: Record<string, unknown> }) {
  const metrics = (result.key_metrics as Record<string, string>) || {};
  const analysis = (result.analysis as string[]) || [];
  const recommendations = (result.recommendations as string[]) || [];

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-base font-bold text-white">{String(result.title || "Report")}</h4>
        <p className="mt-1 text-sm leading-relaxed text-slate-300">{String(result.executive_summary || "")}</p>
      </div>

      {/* Key metrics */}
      <div>
        <h5 className="mb-2 text-xs font-semibold text-slate-200">Key Metrics</h5>
        <div className="flex flex-wrap gap-2">
          {Object.entries(metrics).map(([k, v]) => (
            <span key={k} className="rounded-lg border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-xs text-cyan-200">
              <span className="font-semibold">{k.replace(/_/g, " ")}:</span> {v}
            </span>
          ))}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {[
          { label: "Analysis", items: analysis, col: "text-slate-200" },
          { label: "Recommendations", items: recommendations, col: "text-indigo-200" },
        ].map(({ label, items, col }) => (
          <div key={label} className="rounded-xl border border-white/10 bg-slate-900/40 p-3">
            <h5 className="mb-2 text-xs font-semibold text-slate-200">{label}</h5>
            <ul className="space-y-1.5">
              {items.map((item, i) => (
                <li key={i} className={`text-xs leading-relaxed ${col}`}>• {item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function WorkflowResult({ workflowName, result }: { workflowName: string; result: Record<string, unknown> }) {
  if (workflowName === "financial") return <FinancialResult result={result} />;
  if (workflowName === "consulting") return <ConsultingResult result={result} />;
  if (workflowName === "report") return <ReportResult result={result} />;
  return (
    <pre className="max-h-96 overflow-auto rounded-lg bg-slate-900/70 p-3 text-xs text-slate-200">
      {JSON.stringify(result, null, 2)}
    </pre>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function WorkflowsPage() {
  const { token } = useAuth();
  const { selectedProvider, selectedModel, bedrockCustomModel, openaiApiKey, updatePrefs } = useAppPreferences();

  const [workflows, setWorkflows] = useState<WorkflowMeta[]>([]);
  const [selected, setSelected] = useState<string>("financial");
  const [isRunning, setIsRunning] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<{
    workflow: string;
    steps: string[];
    result: Record<string, unknown>;
    model_used: string;
    provider: string;
    duration_ms: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Local provider/model state so workflows page is independent of chat settings
  const [wfProvider, setWfProvider] = useState(selectedProvider || "openai");
  const [wfModel, setWfModel] = useState(selectedModel || "auto");
  const [wfBedrockCustom, setWfBedrockCustom] = useState(bedrockCustomModel || "");

  const effectiveModel = wfProvider === "bedrock" && wfBedrockCustom.trim()
    ? wfBedrockCustom.trim()
    : wfModel;

  useEffect(() => {
    listWorkflows(token ?? undefined)
      .then((r) => setWorkflows(r.workflows))
      .catch(() => setWorkflows([]));
  }, [token]);

  async function handleSave() {
    if (!runResult) return;
    setIsSaving(true);
    try {
      const res = await saveReport({
        report_type: runResult.workflow,
        title: `${selectedMeta?.label ?? runResult.workflow} — ${new Date().toLocaleDateString()}`,
        data: runResult.result,
        model_used: runResult.model_used,
        provider: runResult.provider,
      }, token ?? undefined);
      setSavedId(res.id);
    } catch {
      // silent — user can retry
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRun() {
    setIsRunning(true);
    setError(null);
    setRunResult(null);
    setSavedId(null);
    try {
      const res = await runWorkflow(
        {
          workflow: selected,
          input: {},
          provider: wfProvider,
          model: effectiveModel,
          openai_api_key: openaiApiKey || null,
        },
        token ?? undefined
      );
      setRunResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow failed.");
    } finally {
      setIsRunning(false);
    }
  }

  const selectedMeta = workflows.find((w) => w.name === selected);

  return (
    <section className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-white">AI Workflows</h2>
        <p className="mt-1 text-sm text-slate-400">
          Multi-step AI pipelines that run automatically against your indexed documents.
          Each workflow runs end-to-end — document retrieval → analysis → structured output.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Left: selector + config */}
        <div className="space-y-4 lg:col-span-1">
          {/* Workflow selector */}
          <article className="rounded-2xl border border-white/15 bg-white/5 p-4">
            <h3 className="mb-3 text-sm font-semibold text-white">Select Workflow</h3>
            <div className="space-y-2">
              {workflows.map((wf) => (
                <button
                  key={wf.name}
                  type="button"
                  onClick={() => { setSelected(wf.name); setRunResult(null); setError(null); }}
                  className={`w-full rounded-xl border p-3 text-left transition ${
                    selected === wf.name
                      ? "border-cyan-400/40 bg-cyan-500/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{WORKFLOW_ICONS[wf.name] ?? "⚙️"}</span>
                    <div>
                      <p className="text-sm font-semibold text-white">{wf.label}</p>
                      <p className="text-xs text-slate-400">{wf.description}</p>
                    </div>
                  </div>
                  {/* Steps preview */}
                  {selected === wf.name && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {wf.steps.map((step, i) => (
                        <span key={step} className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-300">
                          {i > 0 && <ChevronRight className="h-2.5 w-2.5 text-slate-500" />}
                          {step.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              ))}
              {!workflows.length && (
                <p className="text-xs text-slate-400">Loading workflows…</p>
              )}
            </div>
          </article>

          {/* Provider + Model config */}
          <article className="rounded-2xl border border-white/15 bg-white/5 p-4 space-y-3">
            <h3 className="text-sm font-semibold text-white">Model Configuration</h3>

            <label className="block text-xs text-slate-300">
              Provider
              <select
                value={wfProvider}
                onChange={(e) => { const p = e.target.value; setWfProvider(p); setWfModel(p === "bedrock" ? "amazon.nova-lite-v1:0" : "auto"); setWfBedrockCustom(""); }}
                className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
              >
                <option value="openai">☁️  OpenAI  (GPT-4o / GPT-4.1)</option>
                <option value="bedrock">🌩️  AWS Bedrock  (Claude · Nova · Llama)</option>
              </select>
            </label>

            {wfProvider === "openai" ? (
              <label className="block text-xs text-slate-300">
                Model
                <select
                  value={wfModel}
                  onChange={(e) => setWfModel(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                >
                  {["auto", "gpt-4o", "gpt-4.1", "gpt-4.1-mini"].map((m) => (
                    <option key={m} value={m}>{m === "auto" ? "auto (Recommended)" : m}</option>
                  ))}
                </select>
              </label>
            ) : (
              <>
                <label className="block text-xs text-slate-300">
                  Bedrock Model
                  <select
                    value={wfModel}
                    onChange={(e) => { setWfModel(e.target.value); setWfBedrockCustom(""); }}
                    className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                  >
                    <option value="amazon.nova-lite-v1:0">Nova Lite · Amazon (fast)</option>
                    <option value="amazon.nova-micro-v1:0">Nova Micro · Amazon (cheapest)</option>
                    <option value="amazon.nova-pro-v1:0">Nova Pro · Amazon (best quality)</option>
                    <option value="us.anthropic.claude-sonnet-4-5-20251203-v1:0">Claude Sonnet 4.6 · Anthropic</option>
                    <option value="us.anthropic.claude-haiku-3-5-20241022-v1:0">Claude Haiku · Anthropic</option>
                    <option value="us.anthropic.claude-opus-4-5-20251101-v1:0">Claude Opus 4.6 · Anthropic</option>
                    <option value="us.anthropic.claude-opus-4-7-20260416-v1:0">Claude Opus 4.7 · Anthropic (latest)</option>
                  </select>
                </label>
                <label className="block text-xs text-slate-300">
                  Custom Model ID <span className="text-slate-500">(overrides dropdown)</span>
                  <input
                    type="text"
                    value={wfBedrockCustom}
                    onChange={(e) => setWfBedrockCustom(e.target.value)}
                    placeholder="any Bedrock model ID"
                    className="mt-1 w-full rounded-lg border border-cyan-500/30 bg-slate-950/60 px-3 py-2 text-sm text-cyan-100 placeholder-slate-500"
                  />
                </label>
              </>
            )}

            <div className="rounded-lg border border-white/10 bg-slate-900/40 px-3 py-2 text-[11px] text-slate-400">
              Active: <span className="font-mono text-cyan-300">{effectiveModel}</span> via{" "}
              <span className="font-semibold text-slate-300">{wfProvider}</span>
            </div>
          </article>

          {/* Run button */}
          <button
            type="button"
            disabled={isRunning || !selected}
            onClick={handleRun}
            className={`w-full rounded-xl bg-gradient-to-r py-3 text-sm font-semibold text-white shadow-lg transition hover:brightness-110 disabled:opacity-50 ${
              WORKFLOW_COLORS[selected] ?? "from-indigo-500 to-cyan-500"
            }`}
          >
            <span className="flex items-center justify-center gap-2">
              {isRunning
                ? <><Loader2 className="h-4 w-4 animate-spin" /> Running…</>
                : <><Play className="h-4 w-4" /> Run {selectedMeta?.label ?? "Workflow"}</>
              }
            </span>
          </button>
        </div>

        {/* Right: output panel */}
        <div className="lg:col-span-2">
          {!runResult && !isRunning && !error && (
            <div className="flex h-full min-h-64 flex-col items-center justify-center rounded-2xl border border-white/10 border-dashed bg-white/3 text-center p-8">
              <Zap className="mb-3 h-10 w-10 text-slate-600" />
              <p className="text-sm font-semibold text-slate-300">Select a workflow and click Run</p>
              <p className="mt-1 text-xs text-slate-500">
                The workflow will retrieve your indexed documents automatically and produce a structured output.
              </p>
            </div>
          )}

          {isRunning && (
            <div className="flex h-full min-h-64 flex-col items-center justify-center rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-8">
              <Loader2 className="mb-3 h-10 w-10 animate-spin text-cyan-400" />
              <p className="text-sm font-semibold text-white">Running {selectedMeta?.label}…</p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {(selectedMeta?.steps ?? []).map((step) => (
                  <span key={step} className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300 animate-pulse">
                    {step.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {error && !isRunning && (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5">
              <p className="text-sm font-semibold text-red-300">Workflow Failed</p>
              <p className="mt-1 text-xs text-red-200">{error}</p>
            </div>
          )}

          {runResult && !isRunning && (
            <div className="rounded-2xl border border-white/15 bg-white/5 p-5 space-y-4">
              {/* Result header */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-emerald-400" />
                  <h3 className="text-base font-semibold text-white">
                    {WORKFLOW_ICONS[runResult.workflow] ?? "⚙️"} {selectedMeta?.label} Complete
                  </h3>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px]">
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-slate-400">
                    <Clock className="mr-1 inline h-3 w-3" />{runResult.duration_ms}ms
                  </span>
                  <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 font-mono text-cyan-300">
                    {runResult.model_used}
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-slate-300">
                    {runResult.provider}
                  </span>
                </div>
              </div>

              {/* Steps completed */}
              <div className="flex flex-wrap gap-1">
                {runResult.steps.map((step) => (
                  <span key={step} className="flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-300">
                    <CheckCircle className="h-2.5 w-2.5" />
                    {step.replace(/_/g, " ")}
                  </span>
                ))}
              </div>

              {/* Structured output */}
              <WorkflowResult workflowName={runResult.workflow} result={runResult.result} />

              {/* Export + Save buttons */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => downloadJSON(runResult, `${runResult.workflow}-result.json`)}
                  className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/10"
                >
                  <Download className="h-3.5 w-3.5" /> Export JSON
                </button>
                <button
                  type="button"
                  onClick={() => downloadCSV(flattenResult(runResult.result), `${runResult.workflow}-result.csv`)}
                  className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/10"
                >
                  <Download className="h-3.5 w-3.5" /> Export CSV
                </button>
                <button
                  type="button"
                  disabled={isSaving || !!savedId}
                  onClick={handleSave}
                  className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs text-indigo-200 hover:bg-indigo-500/20 disabled:opacity-50"
                >
                  {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  {savedId ? "Saved ✓" : "Save Report"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
