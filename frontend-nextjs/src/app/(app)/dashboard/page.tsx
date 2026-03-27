"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { motion } from "motion/react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getAnalyticsContent,
  getAnalyticsOverview,
  getAnalyticsStorage,
  getHealth,
  getModels,
  listDocuments,
  type DocumentItem,
  type HealthResponse,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

const PIE_COLORS = ["#22d3ee", "#6366f1", "#34d399", "#f59e0b", "#f472b6", "#60a5fa"];
const CAPACITY_LIMIT = 10000;

export default function DashboardPage() {
  const { token } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [content, setContent] = useState<{
    total_estimated_words: number;
    total_reading_time_min: number;
    word_frequencies: Record<string, number>;
  } | null>(null);
  const [overview, setOverview] = useState<{
    total_documents: number;
    total_chunks: number;
    total_size_mb?: number;
    by_category: Record<string, number>;
    by_file_type: Record<string, number>;
    by_status: Record<string, number>;
    by_uploader?: Record<string, number>;
  } | null>(null);
  const [storage, setStorage] = useState<{
    size_by_type: Record<string, number>;
    size_distribution: Record<string, number>;
  } | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);
  const [dateRange, setDateRange] = useState<"24h" | "7d" | "30d" | "all">("30d");
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const heroRef = useRef<HTMLDivElement | null>(null);
  const cardsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!heroRef.current || !cardsRef.current) return;
    gsap.fromTo(
      heroRef.current,
      { opacity: 0, y: 22 },
      { opacity: 1, y: 0, duration: 0.7, ease: "power3.out" }
    );
    gsap.fromTo(
      cardsRef.current.children,
      { opacity: 0, y: 16, scale: 0.98 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.55,
        ease: "power2.out",
        stagger: 0.1,
      }
    );
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);
      const [healthResponse, modelResponse, overviewResponse, contentResponse, storageResponse, docsResponse] =
        await Promise.all([
          getHealth(token ?? undefined),
          getModels(token ?? undefined),
          getAnalyticsOverview(token ?? undefined),
          getAnalyticsContent(token ?? undefined),
          getAnalyticsStorage(token ?? undefined),
          listDocuments(token ?? undefined, 500),
        ]);

      setHealth(healthResponse);
      setModels(modelResponse.models);
      setOverview(overviewResponse);
      setContent(contentResponse);
      setStorage(storageResponse);
      setDocuments(docsResponse.documents);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = window.setInterval(() => {
      void loadDashboard();
    }, refreshInterval * 1000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, refreshInterval, loadDashboard]);

  const filteredDocuments = useMemo(() => {
    if (dateRange === "all") return documents;
    const now = Date.now();
    const cutoffMs =
      dateRange === "24h" ? 24 * 60 * 60 * 1000 : dateRange === "7d" ? 7 * 24 * 60 * 60 * 1000 : 30 * 24 * 60 * 60 * 1000;
    return documents.filter((doc) => {
      if (!doc.timestamp) return false;
      const ts = new Date(doc.timestamp).getTime();
      return Number.isFinite(ts) && now - ts <= cutoffMs;
    });
  }, [dateRange, documents]);

  const dashboardKpis = useMemo(() => {
    const totalDocuments = filteredDocuments.length;
    const totalChunks = filteredDocuments.reduce((sum, item) => sum + (item.chunk_count || 0), 0);
    const totalSizeMb = filteredDocuments.reduce((sum, item) => sum + (item.file_size || 0), 0) / (1024 * 1024);
    const avgChunks = totalDocuments ? totalChunks / totalDocuments : 0;
    const avgSizeMb = totalDocuments ? totalSizeMb / totalDocuments : 0;
    return { totalDocuments, totalChunks, totalSizeMb, avgChunks, avgSizeMb };
  }, [filteredDocuments]);

  const categoryData = useMemo(() => {
    const counter = new Map<string, number>();
    filteredDocuments.forEach((doc) => {
      const key = doc.category || "uncategorized";
      counter.set(key, (counter.get(key) || 0) + 1);
    });
    return [...counter.entries()].map(([name, value]) => ({ name, value }));
  }, [filteredDocuments]);

  const fileTypeData = useMemo(() => {
    const counter = new Map<string, number>();
    filteredDocuments.forEach((doc) => {
      const key = doc.file_type || "unknown";
      counter.set(key, (counter.get(key) || 0) + 1);
    });
    return [...counter.entries()].map(([name, value]) => ({ name, value }));
  }, [filteredDocuments]);

  const timelineData = useMemo(() => {
    const counter = new Map<string, number>();
    filteredDocuments.forEach((doc) => {
      if (!doc.timestamp) return;
      const d = new Date(doc.timestamp);
      if (!Number.isFinite(d.getTime())) return;
      const key = d.toISOString().slice(0, 10);
      counter.set(key, (counter.get(key) || 0) + 1);
    });
    return [...counter.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, value]) => ({ date, value }));
  }, [filteredDocuments]);

  const topCategories = useMemo(
    () => [...categoryData].sort((a, b) => b.value - a.value).slice(0, 8),
    [categoryData]
  );

  const capacityPercent = useMemo(
    () => Math.min(100, Math.round((dashboardKpis.totalDocuments / CAPACITY_LIMIT) * 100)),
    [dashboardKpis.totalDocuments]
  );

  return (
    <section className="space-y-6">
      <div ref={heroRef} className="rounded-2xl border border-white/15 bg-white/5 p-6 backdrop-blur-md">
        <p className="mb-2 inline-block rounded-full border border-indigo-300/35 bg-indigo-500/15 px-3 py-1 text-xs font-medium text-indigo-100">
          Professional Console
        </p>
        <h2 className="text-3xl font-semibold text-white">Intelligence Dashboard</h2>
        <p className="mt-2 text-sm text-slate-300">
          Enterprise analytics view for platform health, documents, content, and storage performance.
        </p>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-300/35 bg-red-500/10 p-4 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      <article className="rounded-xl border border-white/15 bg-white/5 p-4">
        <p className="mb-3 text-xs text-slate-300">Dashboard Controls</p>
        <div className="grid gap-3 md:grid-cols-4">
          <label className="flex items-center justify-between gap-3 rounded-lg border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100">
            Auto refresh
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="h-4 w-4 accent-cyan-400"
            />
          </label>
          <label className="flex items-center gap-2 rounded-lg border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100">
            <span className="shrink-0 text-slate-300">Interval</span>
            <input
              type="number"
              min={5}
              max={120}
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Math.min(120, Math.max(5, Number(e.target.value) || 30)))}
              className="w-full rounded border border-white/20 bg-slate-900/70 px-2 py-1 text-sm text-white"
            />
          </label>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value as "24h" | "7d" | "30d" | "all")}
            className="rounded-lg border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-white"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="all">All Time</option>
          </select>
          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="rounded-lg border border-cyan-300/35 bg-cyan-500/10 px-3 py-2 text-sm font-medium text-cyan-100 hover:bg-cyan-500/20"
          >
            Refresh Now
          </button>
        </div>
      </article>

      <div ref={cardsRef} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <motion.article
          whileHover={{ y: -4 }}
          className="rounded-xl border border-white/15 bg-white/5 p-5 shadow-lg shadow-indigo-950/25 backdrop-blur-md"
        >
          <h3 className="mb-2 text-sm font-medium text-slate-300">Total Documents</h3>
          <p className="text-xl font-semibold text-white">
            {isLoading ? "Loading..." : dashboardKpis.totalDocuments.toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-slate-400">Filtered by selected date range</p>
        </motion.article>

        <motion.article
          whileHover={{ y: -4 }}
          className="rounded-xl border border-white/15 bg-white/5 p-5 shadow-lg shadow-indigo-950/25 backdrop-blur-md"
        >
          <h3 className="mb-2 text-sm font-medium text-slate-300">Knowledge Chunks</h3>
          <p className="text-xl font-semibold text-white">
            {isLoading ? "Loading..." : dashboardKpis.totalChunks.toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-slate-400">{dashboardKpis.avgChunks.toFixed(1)} avg/document</p>
        </motion.article>

        <motion.article
          whileHover={{ y: -4 }}
          className="rounded-xl border border-white/15 bg-white/5 p-5 shadow-lg shadow-indigo-950/25 backdrop-blur-md"
        >
          <h3 className="mb-2 text-sm font-medium text-slate-300">Storage Used</h3>
          <p className="text-xl font-semibold text-white">{dashboardKpis.totalSizeMb.toFixed(1)} MB</p>
          <p className="mt-1 text-xs text-slate-400">{dashboardKpis.avgSizeMb.toFixed(2)} MB avg/document</p>
        </motion.article>

        <motion.article
          whileHover={{ y: -4 }}
          className="rounded-xl border border-white/15 bg-white/5 p-5 shadow-lg shadow-indigo-950/25 backdrop-blur-md"
        >
          <h3 className="mb-2 text-sm font-medium text-slate-300">Backend Health</h3>
          <p className="text-xl font-semibold text-white">
            {health ? `${health.status} (${health.app})` : "Loading..."}
          </p>
          <p className="mt-1 text-xs text-slate-400">{models.length} models available</p>
        </motion.article>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="rounded-xl border border-white/15 bg-white/5 p-5 shadow-lg shadow-indigo-950/25 backdrop-blur-md">
          <h3 className="mb-3 text-sm font-medium text-slate-300">System Capacity</h3>
          <div className="mb-2 flex items-end justify-between">
            <span className="text-2xl font-semibold text-white">{capacityPercent}%</span>
            <span className="text-xs text-slate-400">
              {dashboardKpis.totalDocuments.toLocaleString()} / {CAPACITY_LIMIT.toLocaleString()}
            </span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-indigo-500"
              style={{ width: `${capacityPercent}%` }}
            />
          </div>
        </article>

        <article className="rounded-xl border border-white/15 bg-white/5 p-5 shadow-lg shadow-indigo-950/25 backdrop-blur-md">
          <h3 className="mb-3 text-sm font-medium text-slate-300">Processing Metrics</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={[
                  { name: "Avg Chunks/Doc", value: Number(dashboardKpis.avgChunks.toFixed(2)) },
                  { name: "Avg Size MB/Doc", value: Number(dashboardKpis.avgSizeMb.toFixed(2)) },
                ]}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#cbd5e1" />
                <YAxis stroke="#cbd5e1" />
                <Tooltip />
                <Bar dataKey="value" fill="#22d3ee" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="h-80 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Document Distribution by Category</p>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={categoryData} dataKey="value" nameKey="name" outerRadius={100} label>
                {categoryData.map((_, idx) => (
                  <Cell key={`cat-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </article>

        <article className="h-80 rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Documents by File Type</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={fileTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#cbd5e1" />
              <YAxis stroke="#cbd5e1" />
              <Tooltip />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {fileTypeData.map((_, idx) => (
                  <Cell key={`type-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </article>
      </div>

      <article className="h-80 rounded-xl border border-white/15 bg-white/5 p-4">
        <p className="mb-3 text-xs text-slate-300">Activity Timeline (Uploads)</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={timelineData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" stroke="#cbd5e1" />
            <YAxis stroke="#cbd5e1" />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#60a5fa" strokeWidth={3} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </article>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">Top Categories</p>
          <div className="space-y-2">
            {topCategories.map((item) => (
              <div key={item.name} className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2 text-sm">
                <span className="text-slate-200">{item.name}</span>
                <span className="font-semibold text-cyan-100">{item.value}</span>
              </div>
            ))}
            {!topCategories.length ? <p className="text-sm text-slate-400">No category data available.</p> : null}
          </div>
        </article>

        <article className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="mb-3 text-xs text-slate-300">System Statistics</p>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2">
              <span className="text-slate-300">Estimated Words</span>
              <span className="font-semibold text-white">
                {(content?.total_estimated_words ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2">
              <span className="text-slate-300">Reading Time</span>
              <span className="font-semibold text-white">{(content?.total_reading_time_min ?? 0).toFixed(1)} min</span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2">
              <span className="text-slate-300">File Size Buckets</span>
              <span className="font-semibold text-white">
                {Object.keys(storage?.size_distribution ?? {}).length}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2">
              <span className="text-slate-300">Total Documents (Overview)</span>
              <span className="font-semibold text-white">{(overview?.total_documents ?? 0).toLocaleString()}</span>
            </div>
          </div>
        </article>
      </div>

      

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
          <span className="text-slate-400">Last Updated: </span>
          {lastUpdated ? lastUpdated.toLocaleString() : "N/A"}
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
          <span className="text-slate-400">System Status: </span>
          {health?.status?.toLowerCase() === "healthy" ? "Healthy" : health?.status || "Unknown"}
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
          <span className="text-slate-400">Backend: </span>
          {health ? "Connected" : "Checking..."}
        </div>
      </div>
    </section>
  );
}

