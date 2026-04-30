"use client";

import { useState } from "react";
import {
  AlertTriangle, ArrowRight, BarChart2, CheckCircle,
  Lightbulb, Play, Sparkles, Target, TrendingUp, Zap,
} from "lucide-react";

// ── Static demo data (no backend call needed) ─────────────────────────────────

const DEMO_FINANCIAL = {
  business_insight: {
    summary:
      "The organisation generated a net profit of $850,000 on total revenue of $4.2M, achieving a healthy 20.2% margin. " +
      "Ticket sales remain the dominant revenue stream at 38% of total income, while player salaries account for the " +
      "largest single expense at 41% of total costs. The business is profitable but relies heavily on two revenue lines.",
    key_findings: [
      "Total revenue of $4,200,000 — tickets ($1.6M) and sponsorship ($1.05M) drive 62% of income",
      "Total expenses of $3,350,000 — player salaries ($1.37M) and coach salaries ($440K) = 54% of costs",
      "Net profit: $850,000 | Margin: 20.2% — healthy but below the 25% industry benchmark",
      "F&B revenue ($630K) underperforms relative to stadium capacity — 40% below peer average",
    ],
    risks: [
      "Over-reliance on ticket revenue (38%) creates vulnerability to match cancellations or poor attendance",
      "Player salary inflation could compress margins if not matched by revenue growth",
      "Retail revenue ($320K) is low and represents an underdeveloped channel",
    ],
    recommendations: [
      "Negotiate multi-year sponsorship packages to lock in $1M+ annually and reduce revenue volatility",
      "Launch F&B partnership programme to increase per-seat spend by at least 25%",
      "Introduce retail bundles and online merchandise to double the retail revenue line",
      "Set a hard cap on player salary growth at 5% annually unless revenue grows >10%",
    ],
  },
  result: {
    revenue: { fnb: 630000, sponsorship: 1050000, tickets: 1600000, retail: 320000, player_sales: 600000 },
    expenses: { player_salary: 1372000, coach_salary: 440000, travel: 280000, stadium: 350000, retail: 180000, fnb: 390000, back_office: 220000, misc: 118000 },
    totals: { total_revenue: 4200000, total_expenses: 3350000, net_profit: 850000, margin_pct: 20.2 },
  },
};

const DEMO_CONSULTING = {
  business_insight: {
    summary:
      "The SWOT analysis reveals a business with a strong brand and loyal fan base as its primary competitive advantage. " +
      "However, limited digital revenue and operational inefficiencies represent the biggest drag on growth. " +
      "The most actionable opportunity is launching a digital subscription platform before the next season.",
    key_findings: [
      "Brand strength and stadium location provide a defensible market position",
      "Digital revenue is near-zero despite 80%+ smartphone penetration among the fanbase",
      "Operational costs are 12% above peer benchmarks due to legacy vendor contracts",
      "New government sports-development grants represent $500K+ in available funding",
    ],
    risks: [
      "A key competitor is launching a digital fan-engagement app that could erode loyalty",
      "Dependency on 3 major sponsors — loss of any one would reduce revenue by ~12%",
      "Rising energy costs threaten stadium operating margins",
    ],
    recommendations: [
      "Launch a digital fan platform (app + subscription) within 6 months — estimated $400K ARR by Year 1",
      "Diversify sponsor portfolio by adding 4 mid-tier sponsors at $150K each to reduce concentration risk",
      "Renegotiate the top 3 vendor contracts to align with market rates and save $180K annually",
      "Apply for government sports-development grants — $500K available with a strong application",
    ],
  },
  result: {
    strengths: ["Strong brand recognition and loyal fan base", "Premium stadium location with high footfall", "Experienced management team with 15+ years in sports"],
    weaknesses: ["Limited digital revenue channels", "Legacy vendor contracts 12% above market", "No e-commerce or subscription offering"],
    opportunities: ["Digital fan engagement platform ($400K ARR potential)", "Government sports grants ($500K available)", "Growing international fanbase for merchandise"],
    threats: ["Competitor digital app launch Q3 2026", "Sponsor concentration risk (3 sponsors = 65% of sponsorship revenue)", "Rising energy costs for stadium operations"],
    strategic_actions: ["Launch digital subscription platform in 6 months", "Diversify sponsor portfolio to 10+ sponsors", "Renegotiate top 3 vendor contracts"],
  },
};

const DEMO_REPORT = {
  business_insight: {
    summary:
      "The Q1 2026 performance report confirms the business is on-track against its annual targets, with revenue " +
      "3% ahead of budget and costs 1.5% above plan. Key wins include a new sponsorship deal and strong ticket sales. " +
      "The primary risk is F&B underperformance which needs immediate intervention.",
    key_findings: [
      "Revenue $4.2M vs $4.07M budget — 3.2% ahead of plan",
      "Net profit $850K vs $760K budget — 11.8% above target",
      "Ticket sales 5% above forecast driven by 3 sold-out home matches",
      "F&B revenue 18% below forecast — operational issues identified in catering vendor",
    ],
    risks: [
      "F&B underperformance if unresolved will cost $230K in annual revenue",
      "Costs are tracking 1.5% above plan — needs monitoring to prevent full-year overspend",
    ],
    recommendations: [
      "Replace F&B catering vendor or renegotiate service-level agreement immediately",
      "Accelerate sponsorship activation for remaining $350K uncommitted budget",
      "Review cost centres quarterly to catch overruns early",
    ],
  },
  result: {
    title: "Q1 2026 Business Performance Report",
    executive_summary: "Strong Q1 with revenue 3.2% ahead of plan. Profit up 11.8% vs budget. F&B requires immediate attention.",
    key_metrics: { "Revenue vs Budget": "+3.2%", "Net Profit vs Budget": "+11.8%", "Ticket Sales": "5% above forecast", "F&B Revenue": "18% below forecast", "Cost Overrun": "+1.5%" },
    analysis: ["Revenue outperformance driven by 3 sold-out matches", "Sponsorship income on track with new deal signed", "Player salary costs within budget", "F&B revenue shortfall flagged for action"],
    recommendations: ["Replace or renegotiate F&B vendor", "Review cost overruns before Q2", "Accelerate uncommitted sponsorship activation"],
  },
};

// ── Component: Insight Panel ──────────────────────────────────────────────────
function DemoInsightPanel({ insight, icon, label, color }: {
  insight: typeof DEMO_FINANCIAL["business_insight"];
  icon: string;
  label: string;
  color: string;
}) {
  return (
    <div className={`rounded-2xl border p-5 space-y-4 ${color}`}>
      <div className="flex items-center gap-2">
        <span className="text-xl">{icon}</span>
        <h3 className="text-sm font-semibold text-white">{label}</h3>
        <span className="ml-auto rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300">
          <CheckCircle className="mr-1 inline h-3 w-3" />Demo Data
        </span>
      </div>

      {/* Summary */}
      <div className="rounded-xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/10 to-indigo-500/5 p-4">
        <div className="mb-1.5 flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300">Executive Summary</span>
        </div>
        <p className="text-sm leading-relaxed text-white">{insight.summary}</p>
      </div>

      {/* 3-col grid */}
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-white/4 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <TrendingUp className="h-3.5 w-3.5 text-cyan-300" />
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-300">Key Findings</span>
          </div>
          <ul className="space-y-1.5">
            {insight.key_findings.map((f, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-slate-200">
                <span className="mt-0.5 shrink-0 font-bold text-cyan-300 text-[10px]">{i+1}.</span>{f}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wide text-red-300">Risks</span>
          </div>
          <ul className="space-y-1.5">
            {insight.risks.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-red-200"><span className="mt-0.5 shrink-0">⚠</span>{r}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5 text-indigo-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wide text-indigo-300">Actions</span>
          </div>
          <ul className="space-y-1.5">
            {insight.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-indigo-200"><ArrowRight className="mt-0.5 h-3 w-3 shrink-0" />{r}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function DemoPage() {
  const [active, setActive] = useState<"financial" | "consulting" | "report" | "unified">("unified");
  const [running, setRunning] = useState(false);
  const [shown, setShown] = useState(true);

  function handleRunDemo() {
    setRunning(true);
    setShown(false);
    setTimeout(() => { setShown(true); setRunning(false); }, 1200);
  }

  const demos = [
    { key: "financial" as const, icon: "📊", label: "Financial Analysis", color: "border-emerald-500/30 bg-emerald-500/8", data: DEMO_FINANCIAL },
    { key: "consulting" as const, icon: "💡", label: "Consulting Analysis", color: "border-indigo-500/30 bg-indigo-500/8",  data: DEMO_CONSULTING },
    { key: "report"    as const, icon: "📝", label: "Report Generation",   color: "border-amber-500/30  bg-amber-500/8",    data: DEMO_REPORT    },
  ];

  return (
    <section className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-purple-500/5 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-5 w-5 text-indigo-400" />
              <h2 className="text-2xl font-semibold text-white">Demo Mode</h2>
            </div>
            <p className="text-sm text-slate-300 max-w-lg">
              Explore pre-loaded sample analyses for a sports organisation. This shows exactly what the
              AI produces on your real documents — just with demo data.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRunDemo}
            disabled={running}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 px-5 py-2.5 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60"
          >
            {running ? <><Loader2 className="h-4 w-4 animate-spin" /> Simulating…</> : <><Play className="h-4 w-4" /> Run Demo</>}
          </button>
        </div>
      </div>

      {/* View selector */}
      <div className="flex flex-wrap gap-2">
        {([{ key: "unified", icon: "⚡", label: "Full Analysis" }, ...demos] as Array<{ key: string; icon: string; label: string }>).map((d) => (
          <button
            key={d.key}
            type="button"
            onClick={() => setActive(d.key as typeof active)}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition ${
              active === d.key
                ? "border-cyan-400/40 bg-cyan-500/15 text-white"
                : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
          >
            {d.icon} {d.label}
          </button>
        ))}
      </div>

      {running && (
        <div className="flex items-center gap-3 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-5">
          <Loader2 className="h-6 w-6 animate-spin text-cyan-400 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-white">Simulating full business analysis…</p>
            <p className="text-xs text-slate-400">Retrieving documents → Financial extraction → SWOT → Report → Insights</p>
          </div>
        </div>
      )}

      {shown && !running && (
        <div className="space-y-5">
          {active === "unified" && (
            <>
              {/* Executive strip */}
              <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/8 to-purple-500/5 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="h-5 w-5 text-indigo-400" />
                  <h3 className="text-base font-semibold text-white">Full Business Analysis — Executive Overview</h3>
                  <span className="ml-auto rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300">
                    <CheckCircle className="mr-1 inline h-3 w-3" />All 3 workflows complete
                  </span>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {demos.map((d) => (
                    <div key={d.key} className={`rounded-xl border p-3 ${d.color}`}>
                      <p className="mb-1 text-xs font-semibold text-white">{d.icon} {d.label}</p>
                      <p className="text-xs leading-relaxed text-slate-300 line-clamp-3">{d.data.business_insight.summary}</p>
                    </div>
                  ))}
                </div>
              </div>
              {demos.map((d) => (
                <DemoInsightPanel key={d.key} insight={d.data.business_insight} icon={d.icon} label={d.label} color={d.color} />
              ))}
            </>
          )}

          {active !== "unified" && (() => {
            const d = demos.find((x) => x.key === active)!;
            return <DemoInsightPanel insight={d.data.business_insight} icon={d.icon} label={d.label} color={d.color} />;
          })()}
        </div>
      )}

      {/* CTA */}
      <div className="rounded-2xl border border-white/10 bg-white/3 p-5 text-center">
        <p className="text-sm font-semibold text-white">Ready to analyse your real documents?</p>
        <p className="mt-1 text-xs text-slate-400">Upload documents, then go to Workflows to run live AI analysis.</p>
        <div className="mt-3 flex justify-center gap-3">
          <a href="/documents" className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs text-slate-200 hover:bg-white/10">
            Upload Documents
          </a>
          <a href="/workflows" className="rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-4 py-2 text-xs font-semibold text-white hover:brightness-110">
            Run Live Analysis
          </a>
        </div>
      </div>
    </section>
  );
}

function Loader2({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}
