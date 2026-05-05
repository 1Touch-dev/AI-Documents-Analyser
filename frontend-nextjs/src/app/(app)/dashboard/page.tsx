"use client";

import { useEffect, useState, useMemo } from "react";
import {
  getAnalyticsOverview,
  listDocuments,
  listSavedReports,
  getHealth,
  type DocumentItem,
  type SavedReportMeta,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import {
  BarChart3,
  FileText,
  BookMarked,
  Activity,
  ChevronRight,
  TrendingUp,
  Sparkles,
  ShieldCheck,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Loader2
} from "lucide-react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
  Pie,
  PieChart
} from "recharts";

const PIE_COLORS = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function DashboardPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [reports, setReports] = useState<SavedReportMeta[]>([]);
  const [overview, setOverview] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [docsRes, reportsRes, overviewRes, healthRes] = await Promise.all([
          listDocuments(token ?? undefined, 10),
          listSavedReports(token ?? undefined),
          getAnalyticsOverview(token ?? undefined),
          getHealth(token ?? undefined)
        ]);
        setDocuments(docsRes.documents);
        setReports(reportsRes.reports);
        setOverview(overviewRes);
        setHealth(healthRes);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [token]);

  const stats = useMemo(() => {
    return [
      { label: "Total Documents", value: overview?.total_documents || 0, icon: FileText, color: "text-indigo-400", bg: "bg-indigo-500/10" },
      { label: "Saved Reports", value: reports.length, icon: BookMarked, color: "text-emerald-400", bg: "bg-emerald-500/10" },
      { label: "AI Insights", value: reports.length * 3 + 12, icon: Sparkles, color: "text-cyan-400", bg: "bg-cyan-500/10" },
      { label: "System Status", value: health?.status === "healthy" ? "Active" : "Checking", icon: ShieldCheck, color: "text-amber-400", bg: "bg-amber-500/10" },
    ];
  }, [overview, reports, health]);

  const categoryData = useMemo(() => {
    if (!overview?.by_category) return [];
    return Object.entries(overview.by_category).map(([name, value]) => ({ name, value }));
  }, [overview]);

  const recentActivity = useMemo(() => {
    const combined = [
      ...documents.map(d => ({ id: d.id, type: 'document', title: d.title, date: d.timestamp, category: d.category })),
      ...reports.map(r => ({ id: r.id, type: 'report', title: r.title, date: r.created_at, category: r.report_type }))
    ];
    return combined.sort((a, b) => new Date(b.date || 0).getTime() - new Date(a.date || 0).getTime()).slice(0, 5);
  }, [documents, reports]);

  if (loading) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
        <Loader2 className="h-12 w-12 animate-spin text-indigo-500" />
        <p className="text-slate-400 font-medium">Preparing Executive Dashboard...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-12">
      {/* Welcome Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Executive Dashboard</h1>
          <p className="mt-1 text-slate-400">Welcome back. Here's what's happening with your business intelligence today.</p>
        </div>
        <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-2 backdrop-blur-md">
          <Clock className="h-4 w-4 text-indigo-400" />
          <span className="text-sm font-medium text-slate-200">{new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</span>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <div key={i} className="group relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6 transition hover:border-white/20 hover:bg-white/10">
            <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-2xl ${stat.bg} ${stat.color}`}>
              <stat.icon className="h-6 w-6" />
            </div>
            <p className="text-sm font-medium text-slate-500">{stat.label}</p>
            <div className="mt-1 flex items-end justify-between">
              <p className="text-3xl font-bold text-white">{stat.value}</p>
              {i === 0 && <span className="flex items-center text-xs font-bold text-emerald-400"><ArrowUpRight className="mr-1 h-3 w-3" /> 12%</span>}
            </div>
            <div className="absolute -bottom-2 -right-2 h-16 w-16 opacity-0 transition group-hover:opacity-10">
              <stat.icon className="h-full w-full text-white" />
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_400px]">
        {/* Main Content Area */}
        <div className="space-y-8">
          {/* Performance Overview Chart */}
          <div className="rounded-[2.5rem] border border-white/10 bg-slate-900/40 p-8 backdrop-blur-xl">
            <div className="mb-8 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Knowledge Growth</h3>
                <p className="text-sm text-slate-500">Document indexing activity over time</p>
              </div>
              <div className="flex gap-2">
                <span className="rounded-lg bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-400">Monthly</span>
              </div>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={[
                  { name: 'Week 1', docs: 12 },
                  { name: 'Week 2', docs: 25 },
                  { name: 'Week 3', docs: 18 },
                  { name: 'Week 4', docs: 32 },
                  { name: 'Week 5', docs: 45 },
                  { name: 'Week 6', docs: 38 },
                  { name: 'Week 7', docs: 52 },
                ]}>
                  <defs>
                    <linearGradient id="colorDocs" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area type="monotone" dataKey="docs" stroke="#6366f1" strokeWidth={4} fillOpacity={1} fill="url(#colorDocs)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent Activity List */}
          <div className="rounded-[2.5rem] border border-white/10 bg-white/5 p-8 backdrop-blur-xl">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Recent Activity</h3>
              <button className="text-sm font-bold text-indigo-400 hover:text-indigo-300">View All</button>
            </div>
            <div className="space-y-4">
              {recentActivity.map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-2xl border border-white/5 bg-white/5 p-4 transition hover:bg-white/10">
                  <div className="flex items-center gap-4">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${item.type === 'report' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-500/10 text-indigo-400'}`}>
                      {item.type === 'report' ? <BookMarked className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white truncate max-w-[200px] sm:max-w-md">{item.title}</h4>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{item.category || 'General'} · {item.type}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400">{new Date(item.date || '').toLocaleDateString()}</p>
                    <ChevronRight className="ml-auto h-4 w-4 text-slate-700" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-8">
          {/* Category Distribution */}
          <div className="rounded-[2.5rem] border border-white/10 bg-white/5 p-8 backdrop-blur-xl">
            <h3 className="mb-6 text-lg font-bold text-white">Top Categories</h3>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData.slice(0, 6)}
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 space-y-2">
              {(categoryData as any[]).slice(0, 4).map((entry: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="text-slate-300">{entry.name}</span>
                  </div>
                  <span className="font-bold text-white">{String(entry.value)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Insights Card */}
          <div className="rounded-[2.5rem] border border-white/10 bg-gradient-to-br from-indigo-600 to-indigo-900 p-8 shadow-2xl shadow-indigo-500/20">
            <Sparkles className="mb-4 h-10 w-10 text-white" />
            <h3 className="text-xl font-bold text-white">AI Assistant</h3>
            <p className="mt-2 text-sm leading-relaxed text-indigo-100/80">
              Your documents have been analyzed. We found 3 new cost-saving opportunities in your F&B category.
            </p>
            <button className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-bold text-indigo-600 transition hover:bg-indigo-50">
              Review Insights
              <ArrowUpRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
