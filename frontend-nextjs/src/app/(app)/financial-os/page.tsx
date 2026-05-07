"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import {
  Sparkles,
  TrendingUp,
  Sliders,
  DollarSign,
  Clock,
  AlertTriangle,
  HelpCircle,
  FileText,
  FileSpreadsheet,
  Download,
  ShieldCheck,
  Building,
  Users,
  ChevronRight,
  RefreshCw,
  TrendingDown
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line
} from "recharts";

export default function FinancialOSPage() {
  const { token } = useAuth();

  // Assumption Sliders state
  const [startingCash, setStartingCash] = useState(5000000);
  const [sponsorshipChange, setSponsorshipChange] = useState(0);
  const [payrollChange, setPayrollChange] = useState(0);
  const [refinancingRate, setRefinancingRate] = useState(0.05);
  const [transferSales, setTransferSales] = useState(0);
  const [delayedCollections, setDelayedCollections] = useState(0);
  const [revenueGrowth, setRevenueGrowth] = useState(0.05);
  const [inflation, setInflation] = useState(0.03);
  const [relegationPromo, setRelegationPromo] = useState("none");
  const [selectedScenario, setSelectedScenario] = useState("base");

  // Calculated modeling data state
  const [forecast, setForecast] = useState<any>(null);
  const [intelligence, setIntelligence] = useState<any>(null);
  const [governance, setGovernance] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeNarrativeTab, setActiveNarrativeTab] = useState("board");

  // Trigger recalculations from assumptions
  const runModeling = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch live forecasting metrics
      const forecastRes = await fetch("/api/backend/financial-os/forecast", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          starting_cash: startingCash,
          sponsorship_change_pct: sponsorshipChange,
          payroll_change_pct: payrollChange,
          refinancing_rate: refinancingRate,
          transfer_sales: transferSales,
          delayed_collections_pct: delayedCollections,
          revenue_growth_pct: revenueGrowth,
          inflation_pct: inflation,
          relegation_or_promotion: relegationPromo,
          scenario: selectedScenario
        })
      });
      const forecastData = await forecastRes.json();
      setForecast(forecastData);

      // Extract details for Intelligence synthesis
      const revs = [
        { name: "Main Shirt Sponsorship", amount: 15000000 * (1 + sponsorshipChange), category: "sponsorship" },
        { name: "Stretford End Ticket Sales", amount: 12000000, category: "ticketing" },
        { name: "TV Rights Share", amount: 18000000, category: "media_rights" }
      ];
      const exps = [
        { name: "Squad Salary", amount: 28000000 * (1 + payrollChange), category: "payroll" },
        { name: "Stadium Operations", amount: 8000000, category: "stadium" },
        { name: "Academy Budget", amount: 4000000, category: "academy" }
      ];
      const debts = [
        { name: "Stadium Construction Loan", amount: 50000000, details: { interest_rate: refinancingRate } }
      ];
      const obs = [
        { name: "Quarterly Corporate Taxes", amount: 1200000, category: "taxes", details: { priority: "high" } }
      ];

      // 2. Fetch analytical risks & narratives
      const intelRes = await fetch("/api/backend/financial-os/intelligence", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          starting_cash: startingCash,
          revenue_items: revs,
          expense_items: exps,
          debt_items: debts,
          obligations: obs,
          burn_rate_monthly: forecastData.forecast_30d?.burn_rate || 500000,
          provider: "openai",
          model: "gpt-4o"
        })
      });
      const intelData = await intelRes.json();
      setIntelligence(intelData);

      // 3. Fetch governance and approvals registry
      const govRes = await fetch("/api/backend/financial-os/governance", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      const govData = await govRes.json();
      setGovernance(govData);

    } catch (e) {
      console.error("Modeling calculation failed:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      runModeling();
    }
  }, [
    token,
    startingCash,
    sponsorshipChange,
    payrollChange,
    refinancingRate,
    transferSales,
    delayedCollections,
    revenueGrowth,
    inflation,
    relegationPromo,
    selectedScenario
  ]);

  // Download actions
  const downloadExcel = async () => {
    if (!forecast) return;
    try {
      const res = await fetch("/api/backend/financial-os/export/excel", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          starting_cash: startingCash,
          revenue_items: [
            { name: "Main Shirt Sponsorship", amount: 15000000 * (1 + sponsorshipChange), category: "sponsorship" },
            { name: "Stretford End Ticket Sales", amount: 12000000, category: "ticketing" }
          ],
          expense_items: [
            { name: "Squad Salary", amount: 28000000 * (1 + payrollChange), category: "payroll" }
          ],
          forecast_data: forecast
        })
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Interactive_FPandA_Forecast.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error(e);
    }
  };

  const downloadPptx = async () => {
    if (!intelligence) return;
    try {
      const res = await fetch("/api/backend/financial-os/export/pptx", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          title_text: `${selectedScenario.toUpperCase()} Case - Strategic Financial Briefing`,
          board_summary: intelligence.narratives?.board_summary || "CFO board assessment briefing",
          risks: intelligence.risks || []
        })
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "CFO_Executive_Presentation.pptx";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error(e);
    }
  };

  // Chart parsers
  const getChartData = () => {
    if (!forecast) return [];
    return [
      { name: "30D", Inflow: forecast.forecast_30d.cash_in, Outflow: forecast.forecast_30d.cash_out, Balance: forecast.forecast_30d.ending_cash },
      { name: "60D", Inflow: forecast.forecast_60d.cash_in, Outflow: forecast.forecast_60d.cash_out, Balance: forecast.forecast_60d.ending_cash },
      { name: "90D", Inflow: forecast.forecast_90d.cash_in, Outflow: forecast.forecast_90d.cash_out, Balance: forecast.forecast_90d.ending_cash },
      { name: "180D", Inflow: forecast.forecast_180d.cash_in, Outflow: forecast.forecast_180d.cash_out, Balance: forecast.forecast_180d.ending_cash }
    ];
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-20">
      {/* Hero Section */}
      <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-4 py-1.5 text-xs font-bold text-indigo-400 border border-indigo-500/20">
            <Sparkles className="h-3.5 w-3.5" />
            AI Financial Operating System (Fin-OS)
          </div>
          <h1 className="mt-3 text-4xl font-extrabold tracking-tight text-white lg:text-5xl">
            Treasury & <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">FP&A Modeling</span>
          </h1>
          <p className="mt-2 text-slate-400 max-w-xl">
            Run real-time scenario modeling, liquidity predictions, automated risk audits, and generate CFO-grade narrative briefs.
          </p>
        </div>

        {/* Download Roster */}
        <div className="flex gap-3">
          <button
            onClick={downloadExcel}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-emerald-500/10 px-5 py-3 text-sm font-bold text-emerald-400 hover:bg-emerald-500/20 transition"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Download FP&A Model
          </button>
          <button
            onClick={downloadPptx}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-indigo-500/10 px-5 py-3 text-sm font-bold text-indigo-400 hover:bg-indigo-500/20 transition"
          >
            <FileText className="h-4 w-4" />
            Export CFO Slides
          </button>
        </div>
      </div>

      {/* Main Grid: Control Panel vs Dashboard */}
      <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
        {/* Assumption Controller Sliders */}
        <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 backdrop-blur-xl h-fit space-y-6">
          <div className="flex items-center gap-2 border-b border-white/5 pb-4">
            <Sliders className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white">Scenario Assumptions</h2>
          </div>

          {/* Scenario Selector */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Global Macro Scenario</label>
            <div className="grid grid-cols-2 gap-2">
              {["base", "optimistic", "downside", "emergency"].map((sc) => (
                <button
                  key={sc}
                  onClick={() => setSelectedScenario(sc)}
                  className={`rounded-xl py-2 text-xs font-bold capitalize transition border ${
                    selectedScenario === sc
                      ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/30"
                      : "bg-slate-950/30 text-slate-400 border-white/5 hover:bg-slate-950/50"
                  }`}
                >
                  {sc}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            {/* Starting Cash */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-400 uppercase">Capital Reserves</span>
                <span className="text-white">${startingCash.toLocaleString()}</span>
              </div>
              <input
                type="range"
                min="1000000"
                max="20000000"
                step="500000"
                value={startingCash}
                onChange={(e) => setStartingCash(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>

            {/* Sponsorship Overrides */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-400 uppercase">Sponsorship Variance</span>
                <span className={`text-white ${sponsorshipChange < 0 ? "text-red-400" : "text-emerald-400"}`}>
                  {sponsorshipChange >= 0 ? "+" : ""}{(sponsorshipChange * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="-0.50"
                max="0.50"
                step="0.05"
                value={sponsorshipChange}
                onChange={(e) => setSponsorshipChange(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>

            {/* Payroll Overrides */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-400 uppercase">Payroll Variance</span>
                <span className={`text-white ${payrollChange < 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {payrollChange >= 0 ? "+" : ""}{(payrollChange * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="-0.30"
                max="0.30"
                step="0.05"
                value={payrollChange}
                onChange={(e) => setPayrollChange(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>

            {/* Refinancing Interest Variable */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-400 uppercase">Refinancing Rate</span>
                <span className="text-white">{(refinancingRate * 100).toFixed(1)}%</span>
              </div>
              <input
                type="range"
                min="0.02"
                max="0.15"
                step="0.005"
                value={refinancingRate}
                onChange={(e) => setRefinancingRate(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>

            {/* Cash Collections Delayed */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-400 uppercase">Delayed Collections</span>
                <span className="text-white">{(delayedCollections * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="0.40"
                step="0.05"
                value={delayedCollections}
                onChange={(e) => setDelayedCollections(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>

            {/* Transfer Asset Liquidation */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-400 uppercase">Transfer Asset Liquidation</span>
                <span className="text-emerald-400">+${transferSales.toLocaleString()}</span>
              </div>
              <input
                type="range"
                min="0"
                max="10000000"
                step="1000000"
                value={transferSales}
                onChange={(e) => setTransferSales(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>

            {/* Growth Rates */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-400 uppercase">Organic Growth Rate</span>
                <span className="text-white">{(revenueGrowth * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="-0.05"
                max="0.25"
                step="0.01"
                value={revenueGrowth}
                onChange={(e) => setRevenueGrowth(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Dynamic Forecasting & Visualizations */}
        <div className="space-y-8 min-w-0">
          {forecast ? (
            <>
              {/* Stat Cards Row */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between text-slate-500">
                    <span className="text-xs font-bold uppercase tracking-wider">Runway Days</span>
                    <Clock className="h-4 w-4 text-indigo-400" />
                  </div>
                  <p className="mt-2 text-2xl font-bold text-white">
                    {forecast.forecast_180d.liquidity_runway_days === 999 ? "Infinite" : `${forecast.forecast_180d.liquidity_runway_days} Days`}
                  </p>
                  <p className="text-[10px] text-indigo-400 mt-1">Simulated ending liquidity position</p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between text-slate-500">
                    <span className="text-xs font-bold uppercase tracking-wider">Burn Rate</span>
                    <TrendingDown className="h-4 w-4 text-red-400" />
                  </div>
                  <p className="mt-2 text-2xl font-bold text-red-400">${forecast.forecast_180d.burn_rate.toLocaleString()}/mo</p>
                  <p className="text-[10px] text-slate-500 mt-1">Weighted expenditure velocity</p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between text-slate-500">
                    <span className="text-xs font-bold uppercase tracking-wider">Ending Cash</span>
                    <DollarSign className="h-4 w-4 text-emerald-400" />
                  </div>
                  <p className="mt-2 text-2xl font-bold text-emerald-400">${forecast.forecast_180d.ending_cash.toLocaleString()}</p>
                  <p className="text-[10px] text-slate-500 mt-1">180 days scenario balance</p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between text-slate-500">
                    <span className="text-xs font-bold uppercase tracking-wider">Simulated EBITDA</span>
                    <TrendingUp className="h-4 w-4 text-emerald-400" />
                  </div>
                  <p className="mt-2 text-2xl font-bold text-white">${forecast.forecast_180d.ebitda.toLocaleString()}</p>
                  <p className="text-[10px] text-emerald-400 mt-1">Operating profitability margins</p>
                </div>
              </div>

              {/* Chart Sections */}
              <div className="grid gap-6 md:grid-cols-2">
                {/* Cash Inflow vs Outflow */}
                <div className="rounded-3xl border border-white/10 bg-slate-900/20 p-6">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Cash Inflow vs Outflow</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={getChartData()}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis stroke="#94a3b8" fontSize={11} dataKey="name" />
                        <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(v) => `$${(v / 1e6).toFixed(1)}M`} />
                        <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)" }} />
                        <Legend />
                        <Bar dataKey="Inflow" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Outflow" fill="#ef4444" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Ending Cash balance trend */}
                <div className="rounded-3xl border border-white/10 bg-slate-900/20 p-6">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Liquidity Reserve Projection</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={getChartData()}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis stroke="#94a3b8" fontSize={11} dataKey="name" />
                        <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(v) => `$${(v / 1e6).toFixed(1)}M`} />
                        <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)" }} />
                        <Legend />
                        <Line type="monotone" dataKey="Balance" stroke="#6366f1" strokeWidth={3} dot={{ fill: "#6366f1" }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-3xl border border-dashed border-white/10">
              <RefreshCw className="h-8 w-8 animate-spin text-indigo-400" />
            </div>
          )}

          {/* Tabbed Narratives Synthesis & Intelligence */}
          {intelligence && (
            <div className="grid gap-6 md:grid-cols-2">
              {/* Executive Narratives Briefing tabs */}
              <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-white/5 pb-3">
                  <h3 className="font-bold text-white flex items-center gap-2">
                    <FileText className="h-4 w-4 text-indigo-400" />
                    CFO Executive Narrative
                  </h3>
                  <div className="flex gap-1">
                    {["board", "investor", "lender", "directive"].map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveNarrativeTab(tab)}
                        className={`rounded-lg px-2 py-1 text-[10px] font-bold uppercase tracking-wider transition ${
                          activeNarrativeTab === tab ? "bg-indigo-500 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="text-sm text-slate-300 leading-relaxed min-h-[180px]">
                  {activeNarrativeTab === "board" && <p>{intelligence.narratives?.board_summary}</p>}
                  {activeNarrativeTab === "investor" && <p>{intelligence.narratives?.investor_report}</p>}
                  {activeNarrativeTab === "lender" && <p>{intelligence.narratives?.lender_summary}</p>}
                  {activeNarrativeTab === "directive" && <p>{intelligence.narratives?.management_directive}</p>}
                </div>
              </div>

              {/* Forensic Management Q&As */}
              <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                <h3 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                  <HelpCircle className="h-4 w-4 text-indigo-400" />
                  Forensic Management Q&A
                </h3>

                <div className="space-y-4">
                  {intelligence.questions?.map((q: any, i: number) => (
                    <div key={i} className="rounded-2xl bg-white/5 p-4 space-y-1.5 border border-white/5">
                      <p className="text-xs font-bold text-indigo-300">Q: {q.question}</p>
                      <p className="text-xs text-slate-400">Context: {q.context}</p>
                      <p className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                        <ChevronRight className="h-3 w-3" />
                        Investigation path: {q.suggested_investigation_path}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Risks & Mitigation matrix */}
          {intelligence && (
            <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
              <h3 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                CFO Risk and Compliance Matrix
              </h3>

              <div className="grid gap-4 sm:grid-cols-2">
                {intelligence.risks?.map((risk: any, i: number) => (
                  <div key={i} className="rounded-2xl bg-white/5 p-4 border border-white/5 space-y-2">
                    <div className="flex justify-between items-center">
                      <h4 className="text-sm font-bold text-white">{risk.title}</h4>
                      <span className={`rounded px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                        risk.severity === "critical" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"
                      }`}>
                        {risk.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">{risk.description}</p>
                    <div className="border-t border-white/5 pt-2 mt-1">
                      <p className="text-xs font-bold text-emerald-400">Directive Action:</p>
                      <p className="text-xs text-slate-300 leading-relaxed mt-0.5">{risk.mitigation_action}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Governance & Operations Accountability */}
          {governance && (
            <div className="grid gap-6 md:grid-cols-2">
              {/* Accountability budgets table */}
              <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                <h3 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  Department Budget Variance Accountability
                </h3>

                <div className="space-y-3">
                  {governance.departments?.map((dep: any, i: number) => (
                    <div key={i} className="rounded-2xl bg-white/5 p-4 border border-white/5 space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-white">{dep.department}</span>
                        <span className="text-xs text-slate-400">Owner: {dep.owner}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-center bg-slate-950/40 py-2 rounded-xl border border-white/5">
                        <div>
                          <p className="text-[9px] text-slate-500 uppercase font-bold">Allocated</p>
                          <p className="text-xs font-bold text-white">${(dep.allocated_budget / 1e6).toFixed(1)}M</p>
                        </div>
                        <div>
                          <p className="text-[9px] text-slate-500 uppercase font-bold">Actual</p>
                          <p className="text-xs font-bold text-white">${(dep.actual_spend / 1e6).toFixed(1)}M</p>
                        </div>
                        <div>
                          <p className="text-[9px] text-slate-500 uppercase font-bold">Variance</p>
                          <p className={`text-xs font-bold ${dep.variance < 0 ? "text-red-400" : "text-emerald-400"}`}>
                            {dep.variance_percentage}%
                          </p>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400 italic">"{dep.variance_explanation}"</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Vendor management risk dashboard */}
              <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                <h3 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                  <Building className="h-4 w-4 text-indigo-400" />
                  Vendor Portfolio Concentration & Risk
                </h3>

                <div className="bg-white/5 p-4 rounded-2xl border border-white/5 space-y-4">
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase font-bold">Total Vendor Spend</p>
                      <p className="text-xl font-extrabold text-white">
                        ${(governance.vendor_risk_summary?.total_spend / 1e6).toFixed(1)}M
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase font-bold">Concentration Risk</p>
                      <p className="text-xl font-extrabold text-red-400 uppercase">
                        {governance.vendor_risk_summary?.concentration_risk}
                      </p>
                    </div>
                  </div>

                  <div className="border-t border-white/5 pt-3 space-y-2">
                    <p className="text-xs font-bold text-slate-400 uppercase">Risk Warnings:</p>
                    {governance.vendor_risk_summary?.warnings?.map((warn: string, i: number) => (
                      <p key={i} className="text-xs text-amber-400 flex items-start gap-1">
                        <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                        {warn}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
