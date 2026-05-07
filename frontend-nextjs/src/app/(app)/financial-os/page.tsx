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
  ShieldCheck,
  Building,
  ChevronRight,
  RefreshCw,
  TrendingDown,
  Calendar,
  CheckCircle,
  UserCheck,
  History,
  Info
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

  // Control Drivers State
  const [startingCash, setStartingCash] = useState(5000000);
  const [sponsorshipChange, setSponsorshipChange] = useState(0);
  const [payrollChange, setPayrollChange] = useState(0);
  const [refinancingRate, setRefinancingRate] = useState(0.05);
  const [transferSales, setTransferSales] = useState(0);
  const [delayedCollections, setDelayedCollections] = useState(0);
  const [revenueGrowth, setRevenueGrowth] = useState(0.05);
  const [inflation, setInflation] = useState(0.03);
  const [selectedScenario, setSelectedScenario] = useState("base");

  // Core Orchestrated State
  const [activeTab, setActiveTab] = useState("overview"); // overview | reconciliation | reporting | governance
  const [forecast, setForecast] = useState<any>(null);
  const [reconciliation, setReconciliation] = useState<any>(null);
  const [reports, setReports] = useState<any>(null);
  const [governance, setGovernance] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeReportTemplate, setActiveReportTemplate] = useState("board_report");

  const runInstitutionalFPAPipeline = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Forecast model
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
          relegation_or_promotion: "none",
          scenario: selectedScenario
        })
      });
      const forecastData = await forecastRes.json();
      setForecast(forecastData);

      // 2. Fetch Reconciliation Engine discrepancies & completeness audits
      const reconRes = await fetch("/api/backend/financial-os/reconciliation", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      const reconData = await reconRes.json();
      setReconciliation(reconData);

      // 3. Fetch institutional Board-Grade Report templates
      const reportRes = await fetch("/api/backend/financial-os/executive-reports", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          starting_cash: startingCash,
          revenue_items: [],
          expense_items: [],
          debt_items: [],
          obligations: [],
          burn_rate_monthly: forecastData.forecast_30d?.burn_rate || 500000,
          provider: "openai",
          model: "gpt-4o"
        })
      });
      const reportData = await reportRes.json();
      setReports(reportData);

      // 4. Fetch Governance & Approvals trail
      const govRes = await fetch("/api/backend/financial-os/governance-audit", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      const govData = await govRes.json();
      setGovernance(govData);

    } catch (e) {
      console.error("Institutional FPA pipeline failed:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      runInstitutionalFPAPipeline();
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
    selectedScenario
  ]);

  // Export functions
  const downloadExcel = async () => {
    try {
      const res = await fetch("/api/backend/financial-os/export/excel", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          starting_cash: startingCash,
          revenue_items: [],
          expense_items: [],
          forecast_data: {}
        })
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Linked_Financial_FPandA_Model.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error(e);
    }
  };

  const downloadPptx = async () => {
    try {
      const res = await fetch("/api/backend/financial-os/export/pptx", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          title_text: "Strategic Board & Capital Review",
          board_summary: reports?.board_report?.executive_summary || "Board strategic evaluation",
          risks: []
        })
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Institutional_CFO_Slides.pptx";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error(e);
    }
  };

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
      {/* Hero Header */}
      <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-4 py-1.5 text-xs font-bold text-indigo-400 border border-indigo-500/20">
            <Sparkles className="h-3.5 w-3.5" />
            Unified CFO & FP&A Executive Console
          </div>
          <h1 className="mt-3 text-4xl font-extrabold tracking-tight text-white lg:text-5xl">
            Institutional <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">Financial Operating System</span>
          </h1>
          <p className="mt-2 text-slate-400 max-w-2xl">
            Execute continuous planning forecasts, perform cross-document transaction reconciliation, compile audited Board-grade packages, and monitor automated compliance.
          </p>
        </div>

        {/* Action Downloads */}
        <div className="flex gap-3">
          <button
            onClick={downloadExcel}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-emerald-500/10 px-5 py-3 text-sm font-bold text-emerald-400 hover:bg-emerald-500/20 transition shadow-lg"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Download FP&A Excel Model
          </button>
          <button
            onClick={downloadPptx}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-indigo-500/10 px-5 py-3 text-sm font-bold text-indigo-400 hover:bg-indigo-500/20 transition shadow-lg"
          >
            <FileText className="h-4 w-4" />
            Export CFO Presentation
          </button>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
        
        {/* Continuous Planning Assumptions Panel */}
        <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 backdrop-blur-xl h-fit space-y-6">
          <div className="flex items-center gap-2 border-b border-white/5 pb-4">
            <Sliders className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white">Continuous Planning Drivers</h2>
          </div>

          {/* Macro Scenario Selection */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Continuous Scenario Case</label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: "base", label: "Base Case" },
                { id: "relegation", label: "Downside Case" },
                { id: "promotion", label: "Optimistic Case" },
                { id: "delayed_payments", label: "Cash Crunch Case" }
              ].map((sc) => (
                <button
                  key={sc.id}
                  onClick={() => setSelectedScenario(sc.id)}
                  className={`rounded-xl py-2 px-3 text-xs font-bold transition border text-left ${
                    selectedScenario === sc.id
                      ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/30"
                      : "bg-slate-950/30 text-slate-400 border-white/5 hover:bg-slate-950/50"
                  }`}
                >
                  {sc.label}
                </button>
              ))}
            </div>
          </div>

          {/* Variable Sliders */}
          <div className="space-y-5 pt-2">
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

            {/* Attendance rate */}
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

            {/* Refinancing Rate */}
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

            {/* Cash collections delayed */}
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
                <span className="text-slate-400 uppercase">Asset Liquidation</span>
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
          </div>
        </div>

        {/* Dynamic Executive Dashboard Console */}
        <div className="space-y-8 min-w-0">
          
          {/* Dashboard Navigation Tabs */}
          <div className="flex border-b border-white/10 gap-2 overflow-x-auto pb-px">
            {[
              { id: "overview", label: "Executive Overview & Timeline", icon: Calendar },
              { id: "reconciliation", label: "Financial Reconciliation", icon: ShieldCheck },
              { id: "reporting", label: "Institutional Reporting", icon: FileText },
              { id: "governance", label: "Governance & Automation", icon: UserCheck }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-4 text-sm font-bold border-b-2 transition whitespace-nowrap ${
                  activeTab === tab.id
                    ? "border-indigo-500 text-white"
                    : "border-transparent text-slate-400 hover:text-white"
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="flex h-96 items-center justify-center rounded-3xl border border-dashed border-white/10 bg-slate-900/10">
              <RefreshCw className="h-8 w-8 animate-spin text-indigo-400" />
            </div>
          ) : (
            <>
              {/* TAB 1: EXECUTIVE OVERVIEW & TIMELINE */}
              {activeTab === "overview" && forecast && (
                <div className="space-y-8">
                  {/* KPI metric cards row */}
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                      <div className="flex items-center justify-between text-slate-500">
                        <span className="text-xs font-bold uppercase tracking-wider">Runway Days</span>
                        <Clock className="h-4 w-4 text-indigo-400" />
                      </div>
                      <p className="mt-2 text-2xl font-bold text-white">
                        {forecast.forecast_180d?.liquidity_runway_days === 999 ? "Infinite" : `${forecast.forecast_180d?.liquidity_runway_days} Days`}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-1">Audit status: verified</p>
                    </div>

                    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                      <div className="flex items-center justify-between text-slate-500">
                        <span className="text-xs font-bold uppercase tracking-wider">Burn Rate</span>
                        <TrendingDown className="h-4 w-4 text-red-400" />
                      </div>
                      <p className="mt-2 text-2xl font-bold text-red-400">${forecast.forecast_180d?.burn_rate.toLocaleString()}/mo</p>
                      <p className="text-[10px] text-slate-400 mt-1">Expenditure velocity</p>
                    </div>

                    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                      <div className="flex items-center justify-between text-slate-500">
                        <span className="text-xs font-bold uppercase tracking-wider">Ending Cash</span>
                        <DollarSign className="h-4 w-4 text-emerald-400" />
                      </div>
                      <p className="mt-2 text-2xl font-bold text-emerald-400">${forecast.forecast_180d?.ending_cash.toLocaleString()}</p>
                      <p className="text-[10px] text-slate-400 mt-1">Scenario balance</p>
                    </div>

                    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                      <div className="flex items-center justify-between text-slate-500">
                        <span className="text-xs font-bold uppercase tracking-wider">Simulated EBITDA</span>
                        <TrendingUp className="h-4 w-4 text-emerald-400" />
                      </div>
                      <p className="mt-2 text-2xl font-bold text-white">${forecast.forecast_180d?.ebitda.toLocaleString()}</p>
                      <p className="text-[10px] text-emerald-400 mt-1">Operating profitability</p>
                    </div>
                  </div>

                  {/* Visualizations row */}
                  <div className="grid gap-6 md:grid-cols-2">
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

                    <div className="rounded-3xl border border-white/10 bg-slate-900/20 p-6">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Capital Reserves Forecast</h3>
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

                  {/* Operational Timeline */}
                  <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                    <h3 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                      <Calendar className="h-4 w-4 text-indigo-400" />
                      Operational Maturities & Collections Timeline
                    </h3>
                    <div className="relative border-l border-slate-700 ml-4 pl-6 space-y-6">
                      <div className="relative">
                        <span className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-500 ring-4 ring-slate-950" />
                        <h4 className="text-sm font-bold text-white">May 20 - Season Ticketing Pool Collections</h4>
                        <p className="text-xs text-slate-400 mt-0.5">Estimated $12,000,000 seasonal ticket inflows from Stretford End season holders.</p>
                      </div>
                      <div className="relative">
                        <span className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 ring-4 ring-slate-950" />
                        <h4 className="text-sm font-bold text-white">June 15 - Snapdragon Global Sponsorship Settlement</h4>
                        <p className="text-xs text-slate-400 mt-0.5">Sponsorship collection expected payment of $15,000,000. Under supervision.</p>
                      </div>
                      <div className="relative">
                        <span className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 ring-4 ring-slate-950" />
                        <h4 className="text-sm font-bold text-white">June 30 - HMRC VAT & Corporate Tax Obligation</h4>
                        <p className="text-xs text-slate-400 mt-0.5">Mandatory payment installment of $1,200,000 due. Critical status.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: FINANCIAL RECONCILIATION */}
              {activeTab === "reconciliation" && reconciliation && (
                <div className="space-y-6">
                  {/* Quality Summary Header */}
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-indigo-500/5 p-6">
                    <div className="space-y-1">
                      <h3 className="font-bold text-white flex items-center gap-2 text-lg">
                        <ShieldCheck className="h-5 w-5 text-emerald-400" />
                        Ledger Verification Audit
                      </h3>
                      <p className="text-sm text-slate-400">Validated math totals and cross-document reconciliation links.</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-500 uppercase font-bold">Integrity Score</p>
                      <p className="text-3xl font-black text-emerald-400">{(reconciliation.integrity_score * 100).toFixed(0)}%</p>
                    </div>
                  </div>

                  {/* Duplicate transaction alerts */}
                  <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                    <h4 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      Discrepancies & Duplicate Warnings
                    </h4>
                    {reconciliation.discrepancies?.length > 0 ? (
                      <div className="space-y-3">
                        {reconciliation.discrepancies.map((disc: any, i: number) => (
                          <div key={i} className="flex gap-3 items-start bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4">
                            <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                            <div>
                              <p className="text-sm font-bold text-white">{disc.message}</p>
                              <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider">Severity: {disc.severity}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400">All data reconciliations completed. No transaction discrepancies identified.</p>
                    )}
                  </div>

                  {/* Completeness & verification lists */}
                  <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                    <h4 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                      <CheckCircle className="h-4 w-4 text-emerald-400" />
                      Data Extraction Completeness & Lineage Registry
                    </h4>
                    <div className="grid gap-4 sm:grid-cols-2">
                      {reconciliation.scored_completeness_registry?.map((item: any, i: number) => (
                        <div key={i} className="rounded-2xl bg-white/5 p-4 border border-white/5 space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-bold text-white uppercase tracking-wider">{item.type} Line Item</span>
                            <span className={`rounded-full px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                              item.reconciliation_status === "reconciled" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"
                            }`}>
                              {item.reconciliation_status}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-center bg-slate-950/40 py-2 rounded-xl border border-white/5">
                            <div>
                              <p className="text-[9px] text-slate-500 uppercase font-bold">Completeness</p>
                              <p className="text-xs font-bold text-white">{(item.completeness * 100).toFixed(0)}%</p>
                            </div>
                            <div>
                              <p className="text-[9px] text-slate-500 uppercase font-bold">Confidence</p>
                              <p className="text-xs font-bold text-indigo-400">{(item.confidence * 100).toFixed(0)}%</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: INSTITUTIONAL REPORTING */}
              {activeTab === "reporting" && reports && (
                <div className="space-y-6">
                  {/* Reporting selector */}
                  <div className="flex gap-2 border-b border-white/10 pb-4">
                    {[
                      { id: "board_report", label: "Board Report" },
                      { id: "lender_package", label: "Lender Package" },
                      { id: "investor_briefing", label: "Investor Briefing" },
                      { id: "emergency_liquidity", label: "Emergency Liquidity" },
                      { id: "treasury_briefing", label: "Treasury Briefing" }
                    ].map((rep) => (
                      <button
                        key={rep.id}
                        onClick={() => setActiveReportTemplate(rep.id)}
                        className={`rounded-xl px-4 py-2 text-xs font-bold transition whitespace-nowrap ${
                          activeReportTemplate === rep.id
                            ? "bg-indigo-500 text-white"
                            : "bg-slate-950/30 text-slate-400 hover:text-white"
                        }`}
                      >
                        {rep.label}
                      </button>
                    ))}
                  </div>

                  {/* Render chosen report */}
                  {activeReportTemplate === "board_report" && (
                    <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-6">
                      <div className="border-b border-white/5 pb-4">
                        <div className="flex justify-between items-center">
                          <h3 className="text-xl font-bold text-white">{reports.board_report.metadata.title}</h3>
                          <span className="rounded bg-red-500/20 text-red-400 px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase">
                            {reports.board_report.metadata.classification}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">Compliance confidence rating: {reports.board_report.metadata.compliance_confidence}</p>
                      </div>

                      <div className="space-y-2">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Executive Summary Narrative</h4>
                        <p className="text-sm text-slate-300 leading-relaxed bg-white/5 p-4 rounded-2xl border border-white/5">{reports.board_report.executive_summary}</p>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="rounded-2xl bg-white/5 p-4 border border-white/5 space-y-2">
                          <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Strategic Targets Required Actions</h4>
                          <ul className="text-xs text-slate-300 space-y-1.5 list-disc pl-4">
                            {reports.board_report.required_strategic_actions.map((act: string, i: number) => (
                              <li key={i}>{act}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="rounded-2xl bg-white/5 p-4 border border-white/5 space-y-2">
                          <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Key Compliance Covenants</h4>
                          <ul className="text-xs text-slate-300 space-y-1.5 list-disc pl-4">
                            {reports.board_report.debt_and_covenants.covenants_monitored.map((cov: string, i: number) => (
                              <li key={i}>{cov}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeReportTemplate === "lender_package" && (
                    <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-6">
                      <div className="border-b border-white/5 pb-4">
                        <h3 className="text-xl font-bold text-white">{reports.lender_package.metadata.title}</h3>
                        <p className="text-xs text-emerald-400 mt-1 font-bold">{reports.lender_package.metadata.status}</p>
                      </div>

                      <div className="bg-white/5 p-5 rounded-2xl border border-white/5 space-y-4">
                        <h4 className="text-xs font-bold text-slate-400 uppercase">Lender Debt Servicing Audits</h4>
                        <div className="grid grid-cols-2 gap-4 text-center">
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase font-bold">Outstanding Principal</p>
                            <p className="text-lg font-bold text-white">${(reports.lender_package.debt_servicing_audit.total_facility_principal / 1e6).toFixed(1)}M</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase font-bold">Interest Rate</p>
                            <p className="text-lg font-bold text-indigo-400">{reports.lender_package.debt_servicing_audit.refinancing_interest_rate}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeReportTemplate === "investor_briefing" && (
                    <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-6">
                      <h3 className="text-xl font-bold text-white border-b border-white/5 pb-4">{reports.investor_briefing.metadata.title}</h3>
                      <div className="rounded-2xl bg-white/5 p-4 space-y-3">
                        <p className="text-xs font-bold text-indigo-400 uppercase">Performance Growth Estimates:</p>
                        <p className="text-sm text-slate-300">Annual ticketing demand growth stands at <strong>{reports.investor_briefing.performance_trends.ticketing_organic_growth}</strong>, backed by an average attendance stable rate of <strong>{reports.investor_briefing.performance_trends.attendance_stability}</strong>.</p>
                      </div>
                    </div>
                  )}

                  {activeReportTemplate === "emergency_liquidity" && (
                    <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-6">
                      <div className="border-b border-white/5 pb-4 flex justify-between items-center">
                        <h3 className="text-xl font-bold text-white">{reports.emergency_liquidity.metadata.title}</h3>
                        <span className="rounded bg-red-500/20 text-red-400 px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase">
                          Urgency: {reports.emergency_liquidity.metadata.urgency_level}
                        </span>
                      </div>
                      <div className="rounded-2xl bg-red-500/5 p-4 border border-red-500/20 space-y-3">
                        <p className="text-xs font-bold text-red-400 uppercase">Preservation Deferral Actions Required:</p>
                        <ul className="text-xs text-slate-300 space-y-1.5 list-disc pl-4">
                          {reports.emergency_liquidity.liquidity_preservation_directives.map((dir: string, i: number) => (
                            <li key={i}>{dir}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}

                  {activeReportTemplate === "treasury_briefing" && (
                    <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-6">
                      <h3 className="text-xl font-bold text-white border-b border-white/5 pb-4">{reports.treasury_briefing.metadata.title}</h3>
                      <div className="space-y-4">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Scheduled Liabilities & Taxes Due</h4>
                        <div className="space-y-2">
                          {reports.treasury_briefing.pending_payment_obligations.map((obl: any, i: number) => (
                            <div key={i} className="flex justify-between items-center bg-white/5 p-3 rounded-xl border border-white/5">
                              <div>
                                <p className="text-xs font-bold text-white">{obl.payee} - {obl.category}</p>
                                <p className="text-[10px] text-slate-500">Required date: {obl.due_date}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-xs font-extrabold text-white">${obl.amount.toLocaleString()}</p>
                                <span className="text-[9px] font-bold uppercase text-red-400">{obl.priority} priority</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: GOVERNANCE & AUTOMATION */}
              {activeTab === "governance" && governance && (
                <div className="space-y-8">
                  {/* Approval Lifecycles */}
                  <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                    <h3 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                      <UserCheck className="h-4 w-4 text-emerald-400" />
                      Approval Lifecycle Registry
                    </h3>
                    <p className="text-xs text-slate-400">Tracks corporate authorizations and budget owner overrides.</p>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center bg-white/5 p-4 rounded-xl border border-white/5">
                        <div>
                          <p className="text-xs font-bold text-white">Old Trafford Stadium Roofing Overrun</p>
                          <p className="text-[10px] text-slate-500">Requested by: Collette Roche</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs font-bold text-amber-400 uppercase">PENDING_APPROVAL</p>
                          <p className="text-xs text-slate-300 mt-0.5">$500,000 variance</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Operational Governance Audit Logs */}
                  <div className="rounded-3xl border border-white/10 bg-slate-900/40 p-6 space-y-4">
                    <h3 className="font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                      <History className="h-4 w-4 text-indigo-400" />
                      Continuous Planning Audit Log
                    </h3>
                    <div className="space-y-3 max-h-60 overflow-y-auto">
                      {governance.governance_logs?.map((log: any, i: number) => (
                        <div key={i} className="bg-white/5 p-3 rounded-xl border border-white/5 text-xs space-y-1">
                          <div className="flex justify-between items-center text-[10px] text-slate-500">
                            <span>Actor: {log.actor}</span>
                            <span>{log.timestamp}</span>
                          </div>
                          <p className="font-bold text-white">{log.description}</p>
                          <p className="text-[10px] text-indigo-400 uppercase font-semibold">Event: {log.event_type}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
