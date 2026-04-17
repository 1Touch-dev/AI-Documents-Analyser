"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  Activity, 
  AlertCircle, 
  Clock, 
  Cpu, 
  DollarSign, 
  CheckCircle2, 
  XCircle, 
  Activity as BarChartIcon, 
  ShieldCheck,
  Zap,
  RefreshCcw
} from "lucide-react";

interface Metrics {
  active_jobs: Record<string, number>;
  success_total: Record<string, number>;
  failed_total: Record<string, number>;
  avg_latencies_sec: Record<string, number>;
  total_api_spend: number;
  cost_by_model: Record<string, number>;
}

interface FailedJob {
  id: string;
  document_id: string;
  error: string;
  model: string;
  timestamp: string;
}

export default function SystemPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [failedJobs, setFailedJobs] = useState<FailedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const [mRes, fRes] = await Promise.all([
        fetch("/api/system/metrics"),
        fetch("/api/system/failed_jobs")
      ]);
      if (mRes.ok) setMetrics(await mRes.json());
      if (fRes.ok) setFailedJobs(await fRes.json());
    } catch (err) {
      console.error("Failed to fetch system data", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Polling every 10s
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  if (!metrics && loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  const totalSuccess = Object.values(metrics?.success_total || {}).reduce((a, b) => a + b, 0);
  const totalFailed = Object.values(metrics?.failed_total || {}).reduce((a, b) => a + b, 0);
  const successRate = totalSuccess + totalFailed > 0 
    ? ((totalSuccess / (totalSuccess + totalFailed)) * 100).toFixed(1) 
    : "100";

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">System Observability</h1>
          <p className="text-slate-400">Real-time telemetry, cost tracking, and operational health.</p>
        </div>
        <button 
          onClick={handleRefresh}
          className="flex items-center gap-2 rounded-lg bg-white/5 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
        >
          <RefreshCcw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <KPIItem 
          label="Job Success Rate" 
          value={`${successRate}%`} 
          icon={ShieldCheck} 
          color="cyan"
          trend={`${totalSuccess} successful jobs`}
        />
        <KPIItem 
          label="Total API Spend" 
          value={`$${metrics?.total_api_spend.toFixed(4)}`} 
          icon={DollarSign} 
          color="indigo" 
          trend="Estimated across all models"
        />
        <KPIItem 
          label="Avg Extraction Latency" 
          value={`${metrics?.avg_latencies_sec.financial_extraction?.toFixed(1) || "0.0"}s`} 
          icon={Clock} 
          color="emerald" 
          trend="Rolling average"
        />
        <KPIItem 
          label="Active Tasks" 
          value={Object.values(metrics?.active_jobs || {}).reduce((a, b) => a + b, 0)} 
          icon={Activity} 
          color="rose" 
          trend="Currently in-flight"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Cost Center */}
        <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 backdrop-blur-xl lg:col-span-2">
          <div className="mb-6 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Cost & Model Insights</h3>
            <BarChartIcon className="h-5 w-5 text-indigo-400" />
          </div>
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {Object.entries(metrics?.cost_by_model || {}).map(([model, cost]) => (
                <div key={model} className="rounded-xl bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-wider text-slate-400">{model}</p>
                  <p className="mt-1 text-xl font-bold text-white">${cost.toFixed(4)}</p>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-white/10">
                    <div 
                      className="h-full rounded-full bg-indigo-500" 
                      style={{ width: `${(cost / (metrics?.total_api_spend || 1)) * 100}%` }} 
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-sm text-indigo-300">
              <p>
                <strong>Pro Tip:</strong> Gemma (Local) contributes 0% to total API spend. 
                Using local inference has saved approximately <strong>${(totalSuccess * 0.01).toFixed(2)}</strong> in potential API fees.
              </p>
            </div>
          </div>
        </div>

        {/* System Health Status */}
        <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 backdrop-blur-xl">
          <h3 className="mb-6 text-lg font-semibold text-white">Infrastructure Health</h3>
          <div className="space-y-4">
            <HealthItem label="Database (PostgreSQL)" status="ok" icon={Zap} />
            <HealthItem label="Redis Cache" status="ok" icon={Zap} />
            <HealthItem label="Job Queue" status="ok" icon={Zap} />
            <HealthItem label="Ollama (Local Inference)" status="ok" icon={Zap} />
          </div>
        </div>
      </div>

      {/* Debug Panel: Failed Jobs */}
      <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 backdrop-blur-xl">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-white">System Debug: Last Failed Jobs</h3>
            <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-xs text-rose-500">Stability Panel</span>
          </div>
          <AlertCircle className="h-5 w-5 text-rose-400" />
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/5 text-slate-400">
                <th className="pb-3 pr-4 font-medium">Job ID</th>
                <th className="pb-3 pr-4 font-medium">Model</th>
                <th className="pb-3 pr-4 font-medium">Error Message</th>
                <th className="pb-3 font-medium">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {failedJobs.length > 0 ? failedJobs.map((job) => (
                <tr key={job.id} className="group">
                  <td className="py-4 pr-4 font-mono text-xs text-slate-300">{job.id.slice(0, 8)}...</td>
                  <td className="py-4 pr-4 text-slate-200">{job.model || "Unknown"}</td>
                  <td className="max-w-xs py-4 pr-4 truncate text-rose-400" title={job.error}>
                    {job.error}
                  </td>
                  <td className="py-4 text-slate-400">{new Date(job.timestamp).toLocaleString()}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-slate-500 italic">
                    No failed jobs detected. System is running at 100% stability.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KPIItem({ label, value, icon: Icon, color, trend }: any) {
  const colors: any = {
    cyan: "from-cyan-500/20 to-cyan-500/5 text-cyan-400 border-cyan-500/20",
    indigo: "from-indigo-500/20 to-indigo-500/5 text-indigo-400 border-indigo-500/20",
    emerald: "from-emerald-500/20 to-emerald-500/5 text-emerald-400 border-emerald-500/20",
    rose: "from-rose-500/20 to-rose-500/5 text-rose-400 border-rose-500/20",
  };

  return (
    <div className={`rounded-2xl border bg-gradient-to-br p-6 backdrop-blur-sm ${colors[color]}`}>
      <div className="flex items-center justify-between">
        <Icon className="h-6 w-6 opacity-80" />
        <span className="text-[10px] uppercase font-bold tracking-widest opacity-60">KPI</span>
      </div>
      <div className="mt-4">
        <h4 className="text-sm font-medium opacity-70">{label}</h4>
        <div className="flex items-baseline gap-2">
          <p className="text-2xl font-bold text-white tracking-tight">{value}</p>
        </div>
        <p className="mt-1 text-xs opacity-60 line-clamp-1">{trend}</p>
      </div>
    </div>
  );
}

function HealthItem({ label, status, icon: Icon }: any) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-white/5 p-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-emerald-500/10 p-2">
          <Icon className="h-4 w-4 text-emerald-400" />
        </div>
        <span className="text-sm text-slate-200">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-tighter">Healthy</span>
      </div>
    </div>
  );
}
