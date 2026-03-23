"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Bar as ChartBar } from "react-chartjs-2";
import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
} from "chart.js";
import {
  getAnalyticsContent,
  getAnalyticsContentInsights,
  getAnalyticsOverview,
  getAnalyticsStorage,
  listDocuments,
  type DocumentItem,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const PIE_COLORS = ["#22d3ee", "#6366f1", "#34d399", "#f59e0b", "#f472b6", "#60a5fa"];

type MultiSelectChipProps = {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
};

function MultiSelectChip({ label, options, selected, onChange }: MultiSelectChipProps) {
  function toggleOption(option: string) {
    if (selected.includes(option)) {
      onChange(selected.filter((item) => item !== option));
      return;
    }
    onChange([...selected, option]);
  }

  return (
    <details className="group relative">
      <summary className="flex h-11 cursor-pointer items-center gap-2 rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white marker:content-['']">
        <span className="text-slate-300">{label}:</span>
        <span className="truncate text-slate-100">
          {selected.length ? `${selected.length} selected` : "All"}
        </span>
      </summary>
      <div className="absolute left-0 top-12 z-20 w-full min-w-[220px] rounded-lg border border-white/15 bg-slate-950 p-3 shadow-2xl">
        <div className="max-h-48 space-y-1 overflow-auto">
          {options.map((option) => (
            <label key={option} className="flex items-center gap-2 rounded px-2 py-1 text-xs text-slate-200 hover:bg-white/10">
              <input
                type="checkbox"
                checked={selected.includes(option)}
                onChange={() => toggleOption(option)}
                className="accent-cyan-400"
              />
              <span className="truncate">{option}</span>
            </label>
          ))}
        </div>
        {!!selected.length && (
          <button
            type="button"
            onClick={() => onChange([])}
            className="mt-2 text-xs text-cyan-200 hover:underline"
          >
            Clear
          </button>
        )}
      </div>
    </details>
  );
}

export default function AnalyticsPage() {
  const { token } = useAuth();
  const [content, setContent] = useState<{
    total_estimated_words: number;
    total_reading_time_min: number;
    word_frequencies: Record<string, number>;
  } | null>(null);
  const [contentInsights, setContentInsights] = useState<{
    topics: Array<{ topic: string; frequency: number; type?: string }>;
    entities?: {
      monetary?: Array<{ value: string; occurrences: number }>;
      percentages?: Array<{ value: string; occurrences: number }>;
      dates?: Array<{ value: string; occurrences: number }>;
      emails?: Array<{ value: string; occurrences: number }>;
      urls?: Array<{ value: string; occurrences: number }>;
      organizations?: Array<{ value: string; occurrences: number }>;
    };
    financials?: Array<{
      keyword: string;
      context: string;
      values_found?: string[];
    }>;
    summary: {
      total_topics: number;
      total_entities: number;
      total_financial_items: number;
      docs_analyzed: number;
      chunks_analyzed: number;
    };
  } | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [selectedUploaders, setSelectedUploaders] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [explorerSearch, setExplorerSearch] = useState("");
  const [explorerCategory, setExplorerCategory] = useState("all");
  const [explorerType, setExplorerType] = useState("all");
  const [explorerStatus, setExplorerStatus] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      getAnalyticsOverview(token ?? undefined),
      getAnalyticsContent(token ?? undefined),
      getAnalyticsContentInsights(token ?? undefined),
      getAnalyticsStorage(token ?? undefined),
      listDocuments(token ?? undefined, 500),
    ])
      .then(([, ct, insights, , docs]) => {
        if (!mounted) return;
        setContent(ct);
        setContentInsights(insights);
        setDocuments(docs.documents);

      })
      .catch((e) => mounted && setError(e instanceof Error ? e.message : "Failed to load analytics."));
    return () => {
      mounted = false;
    };
  }, [token]);

  const categories = useMemo(
    () => [...new Set(documents.map((d) => d.category || "uncategorized"))],
    [documents]
  );
  const types = useMemo(() => [...new Set(documents.map((d) => d.file_type || "unknown"))], [documents]);
  const statuses = useMemo(() => [...new Set(documents.map((d) => d.status || "unknown"))], [documents]);
  const uploaders = useMemo(
    () => [...new Set(documents.map((d) => d.uploaded_by || "unknown"))],
    [documents]
  );

  const selectedCategoriesSafe = useMemo(
    () => selectedCategories.filter((v) => categories.includes(v)),
    [categories, selectedCategories]
  );
  const selectedTypesSafe = useMemo(
    () => selectedTypes.filter((v) => types.includes(v)),
    [selectedTypes, types]
  );
  const selectedStatusesSafe = useMemo(
    () => selectedStatuses.filter((v) => statuses.includes(v)),
    [selectedStatuses, statuses]
  );
  const selectedUploadersSafe = useMemo(
    () => selectedUploaders.filter((v) => uploaders.includes(v)),
    [selectedUploaders, uploaders]
  );

  const filteredDocuments = useMemo(() => {
    return documents.filter((d) => {
      const docCategory = d.category || "uncategorized";
      const docType = d.file_type || "unknown";
      const docStatus = d.status || "unknown";
      const docUploader = d.uploaded_by || "unknown";
      const matchesCategory = !selectedCategoriesSafe.length || selectedCategoriesSafe.includes(docCategory);
      const matchesType = !selectedTypesSafe.length || selectedTypesSafe.includes(docType);
      const matchesStatus = !selectedStatusesSafe.length || selectedStatusesSafe.includes(docStatus);
      const matchesUploader = !selectedUploadersSafe.length || selectedUploadersSafe.includes(docUploader);
      const matchesSearch = search.trim()
        ? `${d.title} ${d.category} ${d.file_type} ${d.uploaded_by}`
            .toLowerCase()
            .includes(search.toLowerCase())
        : true;
      return matchesCategory && matchesType && matchesStatus && matchesUploader && matchesSearch;
    });
  }, [
    documents,
    search,
    selectedCategoriesSafe,
    selectedTypesSafe,
    selectedStatusesSafe,
    selectedUploadersSafe,
  ]);

  const docsKpis = useMemo(() => {
    const totalDocuments = filteredDocuments.length;
    const totalChunks = filteredDocuments.reduce((sum, d) => sum + (d.chunk_count || 0), 0);
    const totalSizeMb =
      filteredDocuments.reduce((sum, d) => sum + (d.file_size || 0), 0) / (1024 * 1024);
    return { totalDocuments, totalChunks, totalSizeMb };
  }, [filteredDocuments]);

  const categoryData = useMemo(() => {
    const map = new Map<string, number>();
    filteredDocuments.forEach((d) => map.set(d.category || "uncategorized", (map.get(d.category || "uncategorized") || 0) + 1));
    return [...map.entries()].map(([name, value]) => ({ name, value }));
  }, [filteredDocuments]);

  const statusData = useMemo(() => {
    const map = new Map<string, number>();
    filteredDocuments.forEach((d) => map.set(d.status || "unknown", (map.get(d.status || "unknown") || 0) + 1));
    return [...map.entries()].map(([name, value]) => ({ name, value }));
  }, [filteredDocuments]);

  const sizeByTypeData = useMemo(() => {
    const map = new Map<string, number>();
    filteredDocuments.forEach((d) =>
      map.set(d.file_type || "unknown", (map.get(d.file_type || "unknown") || 0) + (d.file_size || 0) / 1024)
    );
    return [...map.entries()].map(([name, value]) => ({ name, value: Number(value.toFixed(1)) }));
  }, [filteredDocuments]);

  const sizeDistData = useMemo(() => {
    const buckets = { "<100KB": 0, "100KB-1MB": 0, "1MB-10MB": 0, ">10MB": 0 };
    filteredDocuments.forEach((d) => {
      const size = d.file_size || 0;
      if (size < 100 * 1024) buckets["<100KB"] += 1;
      else if (size < 1024 * 1024) buckets["100KB-1MB"] += 1;
      else if (size < 10 * 1024 * 1024) buckets["1MB-10MB"] += 1;
      else buckets[">10MB"] += 1;
    });
    return Object.entries(buckets).map(([name, value]) => ({ name, value }));
  }, [filteredDocuments]);

  const keywordData = Object.entries(content?.word_frequencies ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12)
    .map(([name, value]) => ({ name, value }));
  const topicData = (contentInsights?.topics ?? []).slice(0, 12).map((item) => ({
    name: item.topic,
    value: item.frequency,
    type: item.type || "topic",
  }));
  const monetaryData = (contentInsights?.entities?.monetary ?? []).slice(0, 10);
  const percentageData = (contentInsights?.entities?.percentages ?? []).slice(0, 10);
  const organizationsData = (contentInsights?.entities?.organizations ?? []).slice(0, 10);
  const datesData = (contentInsights?.entities?.dates ?? []).slice(0, 10);
  const contactsData = [
    ...(contentInsights?.entities?.emails ?? []),
    ...(contentInsights?.entities?.urls ?? []),
  ].slice(0, 10);
  const financialContext = (contentInsights?.financials ?? []).slice(0, 10);

  const chartJsTypeData = {
    labels: sizeByTypeData.map((d) => d.name),
    datasets: [
      {
        label: "Size by file type (KB)",
        data: sizeByTypeData.map((d) => d.value),
        backgroundColor: "rgba(34, 211, 238, 0.5)",
        borderColor: "rgba(34, 211, 238, 1)",
        borderWidth: 1,
      },
    ],
  };

  const explorerDocuments = useMemo(() => {
    return filteredDocuments.filter((doc) => {
      const matchesCategory =
        explorerCategory === "all" || (doc.category || "uncategorized") === explorerCategory;
      const matchesType = explorerType === "all" || (doc.file_type || "unknown") === explorerType;
      const matchesStatus = explorerStatus === "all" || (doc.status || "unknown") === explorerStatus;
      const matchesSearch = explorerSearch.trim()
        ? `${doc.title} ${doc.category} ${doc.file_type} ${doc.uploaded_by} ${doc.status}`
            .toLowerCase()
            .includes(explorerSearch.toLowerCase())
        : true;
      return matchesCategory && matchesType && matchesStatus && matchesSearch;
    });
  }, [explorerCategory, explorerSearch, explorerStatus, explorerType, filteredDocuments]);

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-white">Analytics</h2>
        <p className="text-sm text-slate-300">
          Interactive analytics showcase using Recharts + Chart.js in Next.js.
        </p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      <div className="rounded-xl border border-white/15 bg-white/5 p-4">
        <p className="mb-3 text-sm font-semibold text-white">Filters</p>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <MultiSelectChip
            label="Category"
            options={categories}
            selected={selectedCategoriesSafe}
            onChange={setSelectedCategories}
          />
          <MultiSelectChip
            label="Type"
            options={types}
            selected={selectedTypesSafe}
            onChange={setSelectedTypes}
          />
          <MultiSelectChip
            label="Status"
            options={statuses}
            selected={selectedStatusesSafe}
            onChange={setSelectedStatuses}
          />
          <MultiSelectChip
            label="Uploader"
            options={uploaders}
            selected={selectedUploadersSafe}
            onChange={setSelectedUploaders}
          />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documents"
            className="h-11 rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {selectedCategoriesSafe.map((item) => (
            <button
              key={`cat-chip-${item}`}
              type="button"
              onClick={() => setSelectedCategories((prev) => prev.filter((v) => v !== item))}
              className="rounded-full border border-cyan-300/40 bg-cyan-500/15 px-2.5 py-1 text-xs text-cyan-100"
            >
              {item} x
            </button>
          ))}
          {selectedTypesSafe.map((item) => (
            <button
              key={`type-chip-${item}`}
              type="button"
              onClick={() => setSelectedTypes((prev) => prev.filter((v) => v !== item))}
              className="rounded-full border border-indigo-300/40 bg-indigo-500/15 px-2.5 py-1 text-xs text-indigo-100"
            >
              {item} x
            </button>
          ))}
          {selectedStatusesSafe.map((item) => (
            <button
              key={`status-chip-${item}`}
              type="button"
              onClick={() => setSelectedStatuses((prev) => prev.filter((v) => v !== item))}
              className="rounded-full border border-amber-300/40 bg-amber-500/15 px-2.5 py-1 text-xs text-amber-100"
            >
              {item} x
            </button>
          ))}
          {selectedUploadersSafe.map((item) => (
            <button
              key={`uploader-chip-${item}`}
              type="button"
              onClick={() => setSelectedUploaders((prev) => prev.filter((v) => v !== item))}
              className="rounded-full border border-emerald-300/40 bg-emerald-500/15 px-2.5 py-1 text-xs text-emerald-100"
            >
              {item} x
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Documents</p>
          <p className="mt-1 text-2xl font-semibold text-white">{docsKpis.totalDocuments}</p>
        </article>
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Chunks</p>
          <p className="mt-1 text-2xl font-semibold text-white">{docsKpis.totalChunks}</p>
        </article>
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Estimated Words</p>
          <p className="mt-1 text-2xl font-semibold text-white">{content?.total_estimated_words ?? "-"}</p>
        </article>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Size (Filtered)</p>
          <p className="mt-1 text-2xl font-semibold text-white">{docsKpis.totalSizeMb.toFixed(1)} MB</p>
        </article>
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Reading Time</p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {Math.round(content?.total_reading_time_min ?? 0)} min
          </p>
        </article>
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Categories</p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {selectedCategoriesSafe.length || categories.length}
          </p>
        </article>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="h-96 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Topic Intelligence</p>
          {topicData.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topicData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" stroke="#cbd5e1" />
                <YAxis dataKey="name" type="category" width={150} stroke="#cbd5e1" />
                <RechartsTooltip />
                <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                  {topicData.map((entry, idx) => (
                    <Cell
                      key={`topic-${idx}`}
                      fill={entry.type === "bigram" ? "#6366f1" : "#7c3aed"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-300">Topic insights are not available yet.</p>
          )}
        </article>

        <article className="space-y-3 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Theme Tags & Summary</p>
          <div className="flex flex-wrap gap-2">
            {(contentInsights?.topics ?? []).slice(0, 20).map((topic) => (
              <span
                key={topic.topic}
                className={`rounded-full border px-2.5 py-1 text-xs ${
                  topic.type === "bigram"
                    ? "border-indigo-300/40 bg-indigo-500/20 text-indigo-100"
                    : "border-purple-300/35 bg-purple-500/20 text-purple-100"
                }`}
              >
                {topic.topic}
              </span>
            ))}
            {!contentInsights?.topics?.length && (
              <span className="text-sm text-slate-300">No topic tags available.</span>
            )}
          </div>
          {contentInsights?.summary ? (
            <div className="grid gap-2 sm:grid-cols-2">
              <p className="rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-xs text-slate-200">
                Topics: <span className="font-semibold">{contentInsights.summary.total_topics}</span>
              </p>
              <p className="rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-xs text-slate-200">
                Entities: <span className="font-semibold">{contentInsights.summary.total_entities}</span>
              </p>
              <p className="rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-xs text-slate-200">
                Docs analyzed: <span className="font-semibold">{contentInsights.summary.docs_analyzed}</span>
              </p>
              <p className="rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-xs text-slate-200">
                Chunks analyzed: <span className="font-semibold">{contentInsights.summary.chunks_analyzed}</span>
              </p>
            </div>
          ) : null}
        </article>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="space-y-3 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Financial Data Overview</p>
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-200">Monetary Values</p>
            {monetaryData.length ? (
              (() => {
                const maxOccurrences = Math.max(...monetaryData.map((item) => item.occurrences), 1);
                return monetaryData.map((item) => {
                  const widthPercent = Math.max(
                    8,
                    Math.round((item.occurrences / maxOccurrences) * 100)
                  );
                  return (
                    <div
                      key={`money-${item.value}`}
                      className="rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2"
                    >
                      <div className="mb-1 flex items-center justify-between gap-3">
                        <span className="truncate font-mono text-xs text-emerald-100">{item.value}</span>
                        <span className="text-xs font-semibold text-emerald-300">x{item.occurrences}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/10">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400"
                          style={{ width: `${widthPercent}%` }}
                        />
                      </div>
                    </div>
                  );
                });
              })()
            ) : (
              <p className="text-xs text-slate-400">No monetary values detected.</p>
            )}
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-200">Percentages</p>
            {percentageData.length ? (
              <div className="flex flex-wrap gap-2">
                {percentageData.map((item) => (
                  <span
                    key={`pct-${item.value}`}
                    className="rounded-full border border-amber-300/35 bg-amber-500/15 px-2.5 py-1 text-xs text-amber-100"
                  >
                    {item.value} x{item.occurrences}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No percentages detected.</p>
            )}
          </div>
        </article>

        <article className="space-y-2 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-xs text-slate-300">Financial Context Lines</p>
          {financialContext.length ? (
            <div className="max-h-80 space-y-2 overflow-auto pr-1">
              {financialContext.map((item, idx) => (
                <div
                  key={`fin-ctx-${idx}`}
                  className="rounded-lg border border-white/10 bg-slate-950/50 p-3"
                >
                  <p className="inline-block rounded bg-red-500/20 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-red-200">
                    {item.keyword}
                  </p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-200">
                    {item.context.length > 180 ? `${item.context.slice(0, 180)}...` : item.context}
                  </p>
                  {!!item.values_found?.length && (
                    <p className="mt-2 text-[11px] text-slate-400">
                      Values: {item.values_found.slice(0, 3).join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No financial context available.</p>
          )}
        </article>
      </div>

      <article className="space-y-4 rounded-xl border border-white/15 bg-white/5 p-4">
        <p className="text-xs text-slate-300">Entity Intelligence</p>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-200">Organizations</p>
            {organizationsData.length ? (
              organizationsData.map((item) => (
                <div
                  key={`org-${item.value}`}
                  className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2"
                >
                  <span className="truncate text-xs text-slate-100">{item.value}</span>
                  <span className="text-xs font-semibold text-indigo-200">{item.occurrences}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400">No organizations detected.</p>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-200">Dates Referenced</p>
            {datesData.length ? (
              datesData.map((item) => (
                <div
                  key={`date-${item.value}`}
                  className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2"
                >
                  <span className="truncate text-xs text-slate-100">{item.value}</span>
                  <span className="text-xs font-semibold text-amber-200">{item.occurrences}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400">No dates detected.</p>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-200">Contacts & Links</p>
            {contactsData.length ? (
              contactsData.map((item) => (
                <div
                  key={`contact-${item.value}`}
                  className="rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2"
                >
                  <p className="truncate text-xs text-cyan-100">{item.value}</p>
                  <p className="mt-1 text-[11px] text-cyan-300">x{item.occurrences}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400">No contacts/links detected.</p>
            )}
          </div>
        </div>
      </article>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="h-80 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Documents by Category (Recharts Bar)</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={categoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#cbd5e1" />
              <YAxis stroke="#cbd5e1" />
              <RechartsTooltip />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {categoryData.map((_, idx) => (
                  <Cell key={`cat-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="h-80 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Status Share (Recharts Pie)</p>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" outerRadius={100} label>
                {statusData.map((_, idx) => (
                  <Cell key={`status-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Pie>
              <RechartsTooltip />
            </PieChart>
          </ResponsiveContainer>
        </article>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Size by File Type (Chart.js)</p>
          <ChartBar
            data={chartJsTypeData}
            options={{
              responsive: true,
              plugins: {
                legend: { labels: { color: "#e2e8f0" } },
                title: { display: false, text: "" },
              },
              scales: {
                x: { ticks: { color: "#cbd5e1" }, grid: { color: "#334155" } },
                y: { ticks: { color: "#cbd5e1" }, grid: { color: "#334155" } },
              },
            }}
          />
        </article>

        <article className="h-80 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Size Distribution Buckets (Recharts)</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sizeDistData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#cbd5e1" />
              <YAxis stroke="#cbd5e1" />
              <RechartsTooltip />
              <Bar dataKey="value" fill="#a78bfa" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </div>

      <article className="rounded-xl border border-white/15 bg-white/5 p-4">
        <p className="mb-3 text-xs text-slate-300">Data Explorer</p>
        <div className="mb-3 grid gap-2 md:grid-cols-4">
          <input
            value={explorerSearch}
            onChange={(e) => setExplorerSearch(e.target.value)}
            placeholder="Search in explorer..."
            className="h-10 rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-xs text-white"
          />
          <select
            value={explorerCategory}
            onChange={(e) => setExplorerCategory(e.target.value)}
            className="h-10 rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-xs text-white"
          >
            <option value="all">All Categories</option>
            {categories.map((item) => (
              <option key={`exp-cat-${item}`} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            value={explorerType}
            onChange={(e) => setExplorerType(e.target.value)}
            className="h-10 rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-xs text-white"
          >
            <option value="all">All Types</option>
            {types.map((item) => (
              <option key={`exp-type-${item}`} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            value={explorerStatus}
            onChange={(e) => setExplorerStatus(e.target.value)}
            className="h-10 rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-xs text-white"
          >
            <option value="all">All Statuses</option>
            {statuses.map((item) => (
              <option key={`exp-status-${item}`} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="max-h-80 overflow-auto rounded-lg border border-white/10">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/10 text-slate-200">
              <tr>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Uploader</th>
                <th className="px-3 py-2">Chunks</th>
              </tr>
            </thead>
            <tbody>
              {explorerDocuments.slice(0, 200).map((doc) => (
                <tr key={doc.id} className="border-t border-white/10 text-slate-100">
                  <td className="px-3 py-2">{doc.title}</td>
                  <td className="px-3 py-2">{doc.category || "-"}</td>
                  <td className="px-3 py-2">{doc.file_type}</td>
                  <td className="px-3 py-2">{doc.status}</td>
                  <td className="px-3 py-2">{doc.uploaded_by}</td>
                  <td className="px-3 py-2">{doc.chunk_count || 0}</td>
                </tr>
              ))}
              {!explorerDocuments.length && (
                <tr>
                  <td className="px-3 py-3 text-slate-300" colSpan={6}>
                    No documents match explorer filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

