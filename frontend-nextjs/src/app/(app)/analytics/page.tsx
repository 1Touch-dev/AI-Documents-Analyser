"use client";

import { useEffect, useState, useMemo } from "react";
import {
  getAnalyticsContentInsights,
  getFinancialDashboard,
  getAnalyticsOverview,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { 
  BarChart3, 
  TrendingUp, 
  Target, 
  AlertCircle, 
  PieChart as PieIcon, 
  Search, 
  Briefcase, 
  DollarSign, 
  Globe, 
  Calendar,
  Sparkles,
  Loader2
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function AnalyticsPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [financialData, setFinancialData] = useState<any>(null);
  const [insights, setInsights] = useState<any>(null);
  const [overview, setOverview] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [finRes, insightRes, overviewRes] = await Promise.all([
          getFinancialDashboard({ model: "auto" }, token ?? undefined),
          getAnalyticsContentInsights(token ?? undefined),
          getAnalyticsOverview(token ?? undefined)
        ]);
        setFinancialData(finRes);
        setInsights(insightRes);
        setOverview(overviewRes);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const financialChartData = useMemo(() => {
    if (!financialData) return [];
    return [
      ...Object.entries(financialData.revenue || {}).map(([name, value]) => ({ name, value, type: 'revenue' })),
      ...Object.entries(financialData.expenses || {}).map(([name, value]) => ({ name, value, type: 'expense' }))
    ];
  }, [financialData]);

  if (loading) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
        <Loader2 className="h-12 w-12 animate-spin text-indigo-500" />
        <p className="text-slate-400 font-medium">Synthesizing Business Insights...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-12">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">Business Insights</h1>
        <p className="text-slate-400">Deep-dive into extracted intelligence across all your documents.</p>
      </div>

      {/* Financial Health Section */}
      <div className="rounded-[2.5rem] border border-white/10 bg-white/5 p-8 backdrop-blur-xl">
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
              <DollarSign className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Financial Summary</h2>
              <p className="text-xs text-slate-500">Aggregated from multiple sources</p>
            </div>
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-2xl bg-white/5 p-4 border border-white/5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Revenue</p>
                <p className="text-xl font-bold text-emerald-400 mt-1">${financialData?.totals.revenue_total.toLocaleString()}</p>
              </div>
              <div className="rounded-2xl bg-white/5 p-4 border border-white/5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Expenses</p>
                <p className="text-xl font-bold text-red-400 mt-1">${financialData?.totals.expense_total.toLocaleString()}</p>
              </div>
              <div className="rounded-2xl bg-white/5 p-4 border border-white/5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Net Position</p>
                <p className="text-xl font-bold text-cyan-400 mt-1">${financialData?.totals.net_total.toLocaleString()}</p>
              </div>
            </div>
            
            <div className="h-64 w-full rounded-2xl bg-white/2 p-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={financialChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" hide />
                  <YAxis hide />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {financialChartData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.type === 'revenue' ? '#10b981' : '#ef4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-2xl bg-slate-950/50 p-6 border border-white/5 overflow-y-auto max-h-[360px]">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-4">Financial Context Detected</h3>
            <div className="space-y-4">
              {insights?.financials?.map((item: any, i: number) => (
                <div key={i} className="rounded-xl bg-white/5 p-4 border border-white/5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="rounded-lg bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-400 uppercase">{item.keyword}</span>
                    <div className="flex gap-1">
                      {item.values_found?.map((v: string, j: number) => (
                        <span key={j} className="text-[10px] text-emerald-400 font-mono">{v}</span>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed italic">"{item.context}"</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Intelligence Topics */}
        <div className="rounded-[2.5rem] border border-white/10 bg-white/5 p-8 backdrop-blur-xl">
          <div className="mb-6 flex items-center gap-3">
            <Sparkles className="h-6 w-6 text-indigo-400" />
            <h3 className="text-lg font-bold text-white">Dominant Themes</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {insights?.topics?.slice(0, 15).map((topic: any, i: number) => (
              <div 
                key={i} 
                className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/5 px-4 py-2 transition hover:border-indigo-500/30 hover:bg-indigo-500/5"
              >
                <span className="text-sm font-medium text-slate-200">{topic.topic}</span>
                <span className="text-[10px] font-bold text-slate-500">{topic.frequency}</span>
              </div>
            ))}
          </div>
          <div className="mt-8 h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={insights?.topics?.slice(0, 5).map((t: any) => ({ name: t.topic, value: t.frequency }))}
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {insights?.topics?.slice(0, 5).map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="none" />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Entity Intelligence */}
        <div className="rounded-[2.5rem] border border-white/10 bg-white/5 p-8 backdrop-blur-xl">
          <div className="mb-6 flex items-center gap-3">
            <Globe className="h-6 w-6 text-cyan-400" />
            <h3 className="text-lg font-bold text-white">Entity Intelligence</h3>
          </div>
          
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-4">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Key Organizations</h4>
              <div className="space-y-2">
                {insights?.entities?.organizations?.slice(0, 5).map((org: any, i: number) => (
                  <div key={i} className="flex items-center justify-between rounded-xl bg-white/2 p-3 border border-white/5">
                    <span className="text-xs text-slate-300 truncate pr-2">{org.value}</span>
                    <span className="text-[10px] font-bold text-indigo-400">{org.occurrences}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-4">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Timeline Markers</h4>
              <div className="space-y-2">
                {insights?.entities?.dates?.slice(0, 5).map((date: any, i: number) => (
                  <div key={i} className="flex items-center justify-between rounded-xl bg-white/2 p-3 border border-white/5">
                    <span className="text-xs text-slate-300">{date.value}</span>
                    <span className="text-[10px] font-bold text-cyan-400">{date.occurrences}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
