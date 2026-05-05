"use client";

import { useState } from "react";
import { 
  FileOutput, 
  Download, 
  Files, 
  Activity, 
  BarChart3, 
  CheckCircle2, 
  Loader2,
  Table as TableIcon,
  Search
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { API_PROXY_BASE_URL } from "@/lib/config";

export default function ExportDataPage() {
  const { token } = useAuth();
  const [isExporting, setIsExporting] = useState<string | null>(null);

  const handleExport = async (type: string) => {
    setIsExporting(type);
    try {
      // Direct download via window.open with auth token in query if needed, 
      // but usually backend provides an endpoint that returns a file.
      const endpoint = type === 'documents' ? '/export/documents' : type === 'audit' ? '/export/audit' : '/export/analytics';
      window.open(`${API_PROXY_BASE_URL}${endpoint}?token=${token}`, '_blank');
      
      // Simulate completion
      setTimeout(() => setIsExporting(null), 1000);
    } catch (e) {
      setIsExporting(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8 pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">Data Export Center</h1>
        <p className="text-slate-400">Download your platform data for offline analysis or compliance audits.</p>
      </div>

      <div className="grid gap-6">
        {[
          { id: "documents", name: "Document Inventory", desc: "A full list of indexed documents including metadata, size, and category.", icon: Files, color: "indigo" },
          { id: "analytics", name: "Business Analytics", desc: "Aggregated financial data and entity intelligence in CSV format.", icon: BarChart3, color: "emerald" },
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

              <button 
                onClick={() => handleExport(item.id)}
                disabled={!!isExporting}
                className="flex items-center justify-center gap-2 rounded-2xl bg-white/5 border border-white/10 px-8 py-3 text-sm font-bold text-white transition hover:bg-white/10 active:scale-95 disabled:opacity-50"
              >
                {isExporting === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                Export CSV
              </button>
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
