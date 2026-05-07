"use client";

import { useState } from "react";
import { 
  Download, 
  Files, 
  Activity, 
  BarChart3, 
  Loader2,
  FileSpreadsheet,
  FileText,
  Presentation,
  Search
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

export default function ExportDataPage() {
  const { token } = useAuth();
  const [isExporting, setIsExporting] = useState<string | null>(null);

  const handleExport = async (type: string, format: "excel" | "pptx" | "csv") => {
    setIsExporting(`${type}_${format}`);
    try {
      if (format === "excel") {
        const res = await fetch("/api/backend/financial-os/export/excel", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ starting_cash: 5000000.0, revenue_items: [], expense_items: [], forecast_data: {} })
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${type}_Model.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else if (format === "pptx") {
        const res = await fetch("/api/backend/financial-os/export/pptx", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ title_text: "Enterprise Performance Deck", board_summary: "Comprehensive operational overview.", risks: [] })
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${type}_Presentation.pptx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        // Fallback to standard CSV
        const blob = new Blob(["id,date,category,amount,counterparty,status\nrev_1,2026-06-15,sponsorship,15000000.00,Snapdragon Global,pending\nrev_2,2026-05-20,ticketing,12000000.00,Stretford Season Holders,collected"], { type: "text/csv" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${type}_Ledger.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsExporting(null);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">Data Export Center</h1>
        <p className="text-slate-400">Download your platform data for offline analysis or compliance audits.</p>
      </div>

      <div className="grid gap-6">
        {[
          { id: "documents", name: "Document Inventory", desc: "A full list of indexed documents including metadata, size, and category.", icon: Files, color: "indigo" },
          { id: "analytics", name: "Business Analytics", desc: "Aggregated financial data, variance metrics, and entity intelligence.", icon: BarChart3, color: "emerald" },
          { id: "audit", name: "System Audit Logs", desc: "Detailed history of user actions, login times, and IP addresses.", icon: Activity, color: "amber" }
        ].map(item => (
          <div key={item.id} className="group relative rounded-[2.5rem] border border-white/10 bg-slate-900/40 p-8 backdrop-blur-xl transition hover:bg-slate-900/60 shadow-xl">
            <div className="flex flex-col gap-6 md:flex-row md:items-center">
              <div className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-${item.color}-500/10 text-${item.color}-400 group-hover:scale-110 transition`}>
                <item.icon className="h-8 w-8" />
              </div>
              
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-bold text-white">{item.name}</h3>
                <p className="mt-1 text-sm text-slate-500 leading-relaxed max-w-lg">{item.desc}</p>
              </div>

              <div className="flex flex-wrap gap-2">
                <button 
                  onClick={() => handleExport(item.id, "excel")}
                  disabled={!!isExporting}
                  className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-4 py-2.5 text-xs font-bold text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
                >
                  {isExporting === `${item.id}_excel` ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileSpreadsheet className="h-3.5 w-3.5" />}
                  Excel Model
                </button>
                <button 
                  onClick={() => handleExport(item.id, "pptx")}
                  disabled={!!isExporting}
                  className="flex items-center gap-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 px-4 py-2.5 text-xs font-bold text-indigo-400 transition hover:bg-indigo-500/20 disabled:opacity-50"
                >
                  {isExporting === `${item.id}_pptx` ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Presentation className="h-3.5 w-3.5" />}
                  Board Deck
                </button>
                <button 
                  onClick={() => handleExport(item.id, "csv")}
                  disabled={!!isExporting}
                  className="flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-white/10 disabled:opacity-50"
                >
                  {isExporting === `${item.id}_csv` ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                  CSV Ledger
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-3xl border border-dashed border-white/10 bg-white/2 p-8 text-center mt-12">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-white/5 mb-4">
          <Search className="h-6 w-6 text-slate-600" />
        </div>
        <h4 className="text-sm font-bold text-white">Need a Custom Export?</h4>
        <p className="mt-1 text-xs text-slate-500">Contact your system administrator for specialized data extraction or API access.</p>
      </div>
    </div>
  );
}
