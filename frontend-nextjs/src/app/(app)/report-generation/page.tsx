"use client";

import { FormEvent, useState } from "react";
import { generateReport } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { useAppPreferences } from "@/contexts/app-preferences-context";

export default function ReportGenerationPage() {
  const { token } = useAuth();
  const { selectedModel, openaiApiKey, anthropicApiKey, geminiApiKey } = useAppPreferences();
  const [topic, setTopic] = useState("");
  const [query, setQuery] = useState("");
  const [reportType, setReportType] = useState("general");
  const [outputFormat, setOutputFormat] = useState<"markdown" | "table" | "json">("markdown");
  const [report, setReport] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!topic.trim() || !query.trim()) return;
    setError(null);
    setIsGenerating(true);
    try {
      const response = await generateReport(
        {
          topic: topic.trim(),
          query: query.trim(),
          report_type: reportType,
          output_format: outputFormat,
          model: selectedModel || "auto",
          openai_api_key: openaiApiKey || null,
          anthropic_api_key: anthropicApiKey || null,
          gemini_api_key: geminiApiKey || null,
        },
        token ?? undefined
      );
      setReport(response.report || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-white">Report Generation</h2>
        <p className="text-sm text-slate-300">
          Generate AI reports from your document knowledge base.
        </p>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <form onSubmit={onSubmit} className="space-y-3 rounded-xl border border-white/15 bg-white/5 p-5">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Report Topic (e.g. Market Analysis Q4 2025)"
          className="w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
        />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Research Query (e.g. What are the key market trends?)"
          className="w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
        />
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-xs text-slate-300">
            Report Type
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
            >
              <option value="general">general</option>
              <option value="market_analysis">market_analysis</option>
              <option value="financial_summary">financial_summary</option>
              <option value="strategy_comparison">strategy_comparison</option>
            </select>
          </label>
          <label className="text-xs text-slate-300">
            Output Format
            <select
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value as "markdown" | "table" | "json")}
              className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
            >
              <option value="markdown">markdown</option>
              <option value="table">table</option>
              <option value="json">json</option>
            </select>
          </label>
        </div>
        <button
          disabled={isGenerating || !topic.trim() || !query.trim()}
          className="rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {isGenerating ? "Generating..." : "Generate Report"}
        </button>
      </form>

      {report ? (
        <article className="space-y-3 rounded-xl border border-white/15 bg-white/5 p-5">
          <p className="text-sm font-semibold text-white">Generated Report</p>
          <pre className="max-h-[60dvh] overflow-auto rounded-lg border border-white/10 bg-slate-950/60 p-3 text-xs text-slate-100">
            {report}
          </pre>
        </article>
      ) : null}
    </section>
  );
}

