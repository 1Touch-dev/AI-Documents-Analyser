"use client";

import { useEffect, useState } from "react";
import { getUsageSummary, getAuditLogs, type UsageSummary, type AuditEntry } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { Activity, AlertCircle, CheckCircle, Clock, DollarSign, Loader2, ShieldAlert, Zap } from "lucide-react";

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    success: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
    denied:  "bg-red-500/15 text-red-300 border-red-500/20",
    error:   "bg-amber-500/15 text-amber-300 border-amber-500/20",
  };
  const icon = status === "success" ? <CheckCircle className="h-3 w-3" /> :
               status === "denied"  ? <ShieldAlert  className="h-3 w-3" /> :
                                      <AlertCircle  className="h-3 w-3" />;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${map[status] ?? map.error}`}>
      {icon}{status}
    </span>
  );
}

export default function UsagePage() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loadingSum, setLoadingSum] = useState(true);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoadingSum(true);
    getUsageSummary(days, token ?? undefined)
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoadingSum(false));
  }, [token, days]);

  useEffect(() => {
    setLoadingLogs(true);
    getAuditLogs(100, token ?? undefined)
      .then((r) => setLogs(r.logs))
      .catch(() => setLogs([]))
      .finally(() => setLoadingLogs(false));
  }, [token]);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Usage & Audit</h2>
        <p className="mt-1 text-sm text-slate-400">
          LLM cost tracking and security audit trail for all AI operations.
        </p>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Period:</span>
        {[7, 30, 90].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDays(d)}
            className={`rounded-lg border px-3 py-1.5 text-xs transition ${
              days === d
                ? "border-cyan-400/40 bg-cyan-500/15 text-cyan-200"
                : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
          >
            {d}d
          </button>
        ))}
      </div>

      {/* Usage summary cards */}
      {loadingSum ? (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading usage data…
        </div>
      ) : summary ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Total Requests", value: summary.total_requests.toLocaleString(), icon: Activity, color: "text-cyan-300" },
            { label: "Total Tokens", value: summary.total_tokens.toLocaleString(), icon: Zap, color: "text-indigo-300" },
            { label: "Est. Cost (USD) ¹", value: `$${summary.total_cost_usd.toFixed(4)}`, icon: DollarSign, color: "text-emerald-300" },
            { label: "Period", value: `${summary.period_days} days`, icon: Clock, color: "text-slate-300" },
          ].map(({ label, value, icon: Icon, color }) => (
            <article key={label} className="rounded-2xl border border-white/15 bg-white/5 p-4">
              <div className="flex items-center gap-2">
                <Icon className={`h-4 w-4 ${color}`} />
                <p className="text-xs text-slate-400">{label}</p>
              </div>
              <p className={`mt-2 text-xl font-bold ${color}`}>{value}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="text-sm text-red-300">Could not load usage summary.</p>
      )}

      {/* By-model breakdown */}
      {summary && Object.keys(summary.by_model).length > 0 && (
        <article className="rounded-2xl border border-white/15 bg-white/5 p-4">
          <h3 className="mb-3 text-sm font-semibold text-white">Usage by Model</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="pb-2 text-left font-medium text-slate-400">Model</th>
                  <th className="pb-2 text-right font-medium text-slate-400">Requests</th>
                  <th className="pb-2 text-right font-medium text-slate-400">Tokens</th>
                  <th className="pb-2 text-right font-medium text-slate-400">Est. Cost</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.by_model).map(([model, stats]) => (
                  <tr key={model} className="border-t border-white/5">
                    <td className="py-2 font-mono text-cyan-300">{model}</td>
                    <td className="py-2 text-right text-slate-200">{stats.requests}</td>
                    <td className="py-2 text-right text-slate-200">{stats.tokens.toLocaleString()}</td>
                    <td className="py-2 text-right text-emerald-300">${stats.cost.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}

      {summary && Object.keys(summary.by_model).length === 0 && !loadingSum && (
        <p className="text-sm text-slate-400">No LLM usage recorded yet. Run a workflow or skill to generate data.</p>
      )}

      {summary && (
        <p className="text-xs text-slate-500">
          ¹ <strong className="text-slate-400">Estimated cost</strong> — token counts are approximated from response
          character length (~4 chars/token). Actual API costs may differ slightly.
        </p>
      )}

      {/* Audit log */}
      <article className="rounded-2xl border border-white/15 bg-white/5 p-4">
        <h3 className="mb-3 text-sm font-semibold text-white">Audit Trail</h3>
        {loadingLogs ? (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading audit logs…
          </div>
        ) : logs.length === 0 ? (
          <p className="text-xs text-slate-400">No audit entries yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="pb-2 text-left font-medium text-slate-400">Time</th>
                  <th className="pb-2 text-left font-medium text-slate-400">Action</th>
                  <th className="pb-2 text-left font-medium text-slate-400">Resource</th>
                  <th className="pb-2 text-left font-medium text-slate-400">User</th>
                  <th className="pb-2 text-left font-medium text-slate-400">Status</th>
                  <th className="pb-2 text-left font-medium text-slate-400">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-t border-white/5 hover:bg-white/3">
                    <td className="py-1.5 text-slate-400">{log.timestamp.slice(0, 19).replace("T", " ")}</td>
                    <td className="py-1.5 font-mono text-cyan-200">{log.action}</td>
                    <td className="py-1.5 text-slate-300">{log.resource ?? "-"}</td>
                    <td className="py-1.5 text-slate-200">{log.username ?? "anon"}</td>
                    <td className="py-1.5"><StatusPill status={log.status} /></td>
                    <td className="py-1.5 font-mono text-slate-400">{log.ip_address ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}
