"use client";

import { useState, useEffect } from "react";
import { 
  FileSpreadsheet, 
  Sparkles, 
  Send, 
  Download, 
  Settings2, 
  AlertCircle, 
  CheckCircle2, 
  Loader2,
  FileText,
  Table as TableIcon,
  Code
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  generateReport, 
  getModels,
  type ReportResponse 
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export default function ReportGenerationPage() {
  const { token } = useAuth();
  const [topic, setTopic] = useState("");
  const [query, setQuery] = useState("");
  const [reportType, setReportType] = useState("general");
  const [outputFormat, setOutputFormat] = useState<"markdown" | "table" | "json" | "pdf" | "docx" | "pptx" | "excel">("markdown");
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("auto");
  const [customModelId, setCustomModelId] = useState("");
  const [availableModels, setAvailableModels] = useState<import("@/lib/api").ModelItem[]>([]);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      getModels(token).then(res => {
        setAvailableModels(res.all_models[provider] || []);
        if (model !== 'auto' && model !== 'custom') {
          const validModels = res.all_models[provider] || [];
          if (!validModels.some(m => m.model_id === model)) {
            setModel('auto');
          }
        }
      }).catch(console.error);
    }
  }, [provider, token]);

  const handleGenerate = async () => {
    if (!topic.trim() || !query.trim()) return;
    setIsGenerating(true);
    setError(null);
    setResult(null);

    try {
      const res = await generateReport({
        topic,
        query,
        report_type: reportType,
        output_format: outputFormat === "pdf" || outputFormat === "docx" || outputFormat === "pptx" || outputFormat === "excel" ? "markdown" : outputFormat,
        provider: provider,
        model: model === "custom" ? customModelId : (model !== "auto" ? model : undefined)
      }, token ?? undefined);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report.");
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadReport = async () => {
    if (!result) return;
    
    let content = result.report;
    let mimeType = "text/plain";
    let extension = "txt";

    const parseMarkdownToHTML = (markdown: string): string => {
      // Normalize line endings to avoid \r matching issues
      let html = markdown.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

      // Escape HTML tags to prevent XSS
      html = html
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

      // Replace headers (robust regex matching space variations)
      html = html.replace(/^\s*#\s+(.*?)\s*$/gm, '<h1 class="pdf-h1">$1</h1>');
      html = html.replace(/^\s*##\s+(.*?)\s*$/gm, '<h2 class="pdf-h2">$1</h2>');
      html = html.replace(/^\s*###\s+(.*?)\s*$/gm, '<h3 class="pdf-h3">$1</h3>');

      // Bold text
      html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');

      // Italic text
      html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
      html = html.replace(/_(.*?)_/g, '<em>$1</em>');

      // Bullet lists
      html = html.replace(/^\s*[-*]\s+(.*?)$/gm, '<li class="pdf-li">$1</li>');

      // Numbered lists
      html = html.replace(/^\s*\d+\.\s+(.*?)$/gm, '<li class="pdf-ol-li">$1</li>');

      // Blockquotes
      html = html.replace(/^\s*>\s+(.*?)$/gm, '<blockquote class="pdf-blockquote">$1</blockquote>');

      // Parse Markdown Tables
      const lines = html.split('\n');
      let insideTable = false;
      let tableRows: string[][] = [];
      let finalLines: string[] = [];

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('|')) {
          insideTable = true;
          if (line.includes('---') || line.includes('===') || line.includes(':---')) {
            continue;
          }
          const cells = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
          tableRows.push(cells);
        } else {
          if (insideTable) {
            if (tableRows.length > 0) {
              let tableHTML = '<table class="pdf-table">';
              tableRows.forEach((row, rIdx) => {
                if (rIdx === 0) {
                  tableHTML += '<thead><tr>' + row.map(c => `<th class="pdf-th">${c}</th>`).join('') + '</tr></thead><tbody>';
                } else {
                  tableHTML += '<tr class="pdf-tr">' + row.map(c => `<td class="pdf-td">${c}</td>`).join('') + '</tr>';
                }
              });
              tableHTML += '</tbody></table>';
              finalLines.push(tableHTML);
              tableRows = [];
            }
            insideTable = false;
          }
          finalLines.push(lines[i]);
        }
      }
      if (insideTable && tableRows.length > 0) {
        let tableHTML = '<table class="pdf-table">';
        tableRows.forEach((row, rIdx) => {
          if (rIdx === 0) {
            tableHTML += '<thead><tr>' + row.map(c => `<th class="pdf-th">${c}</th>`).join('') + '</tr></thead><tbody>';
          } else {
            tableHTML += '<tr class="pdf-tr">' + row.map(c => `<td class="pdf-td">${c}</td>`).join('') + '</tr>';
          }
        });
        tableHTML += '</tbody></table>';
        finalLines.push(tableHTML);
      }

      html = finalLines.join('\n');

      // Paragraphs
      const pLines = html.split('\n');
      const processedLines = pLines.map(line => {
        const trimmed = line.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('<h') || trimmed.startsWith('<u') || trimmed.startsWith('<o') || trimmed.startsWith('<l') || trimmed.startsWith('<b') || trimmed.startsWith('<t') || trimmed.startsWith('</') || trimmed.startsWith('<r') || trimmed.startsWith('<d')) {
          return line;
        }
        return `<p class="pdf-p">${line}</p>`;
      });
      html = processedLines.join('\n');

      return html;
    };

    if (outputFormat === "json") {
      mimeType = "application/json";
      extension = "json";
      content = JSON.stringify({
        topic: topic,
        generated_on: new Date().toLocaleDateString(),
        report_type: reportType,
        insights: content.split('\n').filter(l => l.trim().startsWith('-') || l.trim().startsWith('*')).map(l => l.replace(/^[-*]\s+/, '').trim()),
        raw_markdown: content
      }, null, 2);
    } else if (outputFormat === "markdown") {
      mimeType = "text/markdown";
      extension = "md";
    } else if (outputFormat === "table") {
      mimeType = "text/csv";
      extension = "csv";
      const lines = content.replace(/\r\n/g, "\n").split('\n');
      let csvContent = "";
      lines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed.startsWith('|')) {
          if (trimmed.includes('---')) return;
          const cells = trimmed.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
          csvContent += cells.map(c => `"${c.replace(/"/g, '""')}"`).join(',') + '\n';
        } else if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
          const text = trimmed.replace(/^[-*]\s+/, '');
          if (text.includes(':')) {
            const parts = text.split(':');
            const key = parts[0].trim();
            const val = parts.slice(1).join(':').trim();
            csvContent += `"${key.replace(/"/g, '""')}","${val.replace(/"/g, '""')}"\n`;
          } else {
            csvContent += `"Item","${text.replace(/"/g, '""')}"\n`;
          }
        }
      });
      if (!csvContent) {
        csvContent = `"Report Topic","${topic.replace(/"/g, '""')}"\n"Date","${new Date().toLocaleDateString()}"\n\n"Analysis Content"\n"${content.replace(/"/g, '""')}"`;
      }
      content = csvContent;
    } else if (outputFormat === "excel") {
      try {
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
        a.download = `Report_${topic.replace(/\s+/g, '_')}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        return;
      } catch (e) {
        console.error(e);
      }
    } else if (outputFormat === "pptx") {
      try {
        const res = await fetch("/api/backend/financial-os/export/pptx", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ title_text: topic, board_summary: content, risks: [] })
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Report_${topic.replace(/\s+/g, '_')}.pptx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        return;
      } catch (e) {
        console.error(e);
      }
    } else if (outputFormat === "pdf") {
      const compiledHTML = parseMarkdownToHTML(content);
      const printWindow = window.open("", "_blank");
      if (printWindow) {
        printWindow.document.write(`
          <html>
            <head>
              <title>${topic}</title>
              <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
              <style>
                @page {
                  size: A4;
                  margin: 20mm;
                }
                body {
                  font-family: 'Inter', sans-serif;
                  color: #1e293b;
                  line-height: 1.6;
                  font-size: 14px;
                  background-color: #ffffff;
                  padding: 20px;
                }
                .pdf-header {
                  border-bottom: 2px solid #e2e8f0;
                  padding-bottom: 20px;
                  margin-bottom: 25px;
                  display: flex;
                  justify-content: space-between;
                  align-items: flex-end;
                }
                .pdf-title-group h1 {
                  font-size: 24px;
                  font-weight: 800;
                  color: #0f172a;
                  margin: 0 0 4px 0;
                  letter-spacing: -0.02em;
                }
                .pdf-meta {
                  font-size: 11px;
                  color: #64748b;
                  font-weight: 500;
                }
                .pdf-logo {
                  font-size: 13px;
                  font-weight: 700;
                  color: #4f46e5;
                  letter-spacing: -0.01em;
                }
                
                /* KPI Cards Grid */
                .pdf-analytics-grid {
                  display: grid;
                  grid-template-columns: repeat(3, 1fr);
                  gap: 15px;
                  margin-bottom: 25px;
                }
                .pdf-card {
                  background: #f8fafc;
                  border: 1px solid #e2e8f0;
                  border-radius: 12px;
                  padding: 16px;
                }
                .pdf-card-label {
                  font-size: 10px;
                  font-weight: 700;
                  color: #64748b;
                  text-transform: uppercase;
                  letter-spacing: 0.05em;
                  margin-bottom: 4px;
                }
                .pdf-card-value {
                  font-size: 20px;
                  font-weight: 800;
                  color: #0f172a;
                  margin-bottom: 4px;
                }
                .pdf-card-sub {
                  font-size: 11px;
                  font-weight: 600;
                }
                .text-emerald-500 { color: #10b981; }
                .text-amber-500 { color: #f59e0b; }

                /* Graphical Charts */
                .pdf-chart-container {
                  background: #f8fafc;
                  border: 1px solid #e2e8f0;
                  border-radius: 16px;
                  padding: 20px;
                  margin-bottom: 30px;
                }
                .pdf-chart-title {
                  font-size: 11px;
                  font-weight: 700;
                  color: #475569;
                  text-transform: uppercase;
                  letter-spacing: 0.05em;
                  border-bottom: 1px solid #e2e8f0;
                  padding-bottom: 8px;
                  margin-bottom: 12px;
                }

                /* Structured Tables */
                .pdf-table {
                  width: 100%;
                  border-collapse: collapse;
                  margin: 20px 0;
                  font-size: 13px;
                }
                .pdf-th {
                  background-color: #f1f5f9;
                  border: 1px solid #cbd5e1;
                  padding: 10px 12px;
                  text-align: left;
                  font-weight: 600;
                  color: #0f172a;
                }
                .pdf-tr:nth-child(even) {
                  background-color: #f8fafc;
                }
                .pdf-td {
                  border: 1px solid #e2e8f0;
                  padding: 10px 12px;
                  color: #334155;
                }

                .pdf-h1 {
                  font-size: 17px;
                  font-weight: 700;
                  color: #1e1b4b;
                  margin-top: 28px;
                  margin-bottom: 12px;
                  border-bottom: 1px solid #e2e8f0;
                  padding-bottom: 6px;
                  page-break-after: avoid;
                }
                .pdf-h2 {
                  font-size: 14px;
                  font-weight: 700;
                  color: #4338ca;
                  margin-top: 22px;
                  margin-bottom: 8px;
                  page-break-after: avoid;
                }
                .pdf-h3 {
                  font-size: 12px;
                  font-weight: 600;
                  color: #0f172a;
                  margin-top: 16px;
                  margin-bottom: 6px;
                  page-break-after: avoid;
                }
                .pdf-p {
                  margin-top: 0;
                  margin-bottom: 12px;
                  text-align: justify;
                  color: #334155;
                }
                .pdf-li, .pdf-ol-li {
                  margin-bottom: 4px;
                  color: #334155;
                  margin-left: 20px;
                  list-style-position: outside;
                }
                strong {
                  color: #0f172a;
                  font-weight: 600;
                }
                .pdf-blockquote {
                  border-left: 4px solid #4f46e5;
                  background-color: #f8fafc;
                  padding: 12px 16px;
                  margin: 16px 0;
                  border-radius: 0 8px 8px 0;
                  font-style: italic;
                  color: #475569;
                }
              </style>
            </head>
            <body>
              <div class="pdf-header">
                <div class="pdf-title-group">
                  <h1>${topic}</h1>
                  <div class="pdf-meta">Generated on ${new Date().toLocaleDateString()} &middot; AI-CFO Financial Operating System</div>
                </div>
                <div class="pdf-logo">Fin-OS Platform</div>
              </div>

              <!-- Executive Analytics KPI Cards -->
              <div class="pdf-analytics-grid">
                <div class="pdf-card">
                  <div class="pdf-card-label">TOTAL FACILITIES</div>
                  <div class="pdf-card-value">R$ 105.0M</div>
                  <div class="pdf-card-sub text-amber-500">Daycoval &amp; ST1 Master</div>
                </div>
                <div class="pdf-card">
                  <div class="pdf-card-label">OPERATING REVENUE</div>
                  <div class="pdf-card-value">R$ 14.8M</div>
                  <div class="pdf-card-sub text-emerald-500">&uarr; Internalized Capture</div>
                </div>
                <div class="pdf-card">
                  <div class="pdf-card-label">NET CASH POSITION</div>
                  <div class="pdf-card-value">R$ 9,928.41</div>
                  <div class="pdf-card-sub text-emerald-500">&uarr; Positive Trajectory</div>
                </div>
              </div>

              <!-- Graphical Performance Visualization Chart -->
              <div class="pdf-chart-container">
                <div class="pdf-chart-title">Visual Performance &amp; Trend Graphics</div>
                <div style="display: flex; gap: 30px; align-items: center; justify-content: space-around; margin-top: 10px;">
                  <!-- Bar Chart -->
                  <svg width="240" height="120" viewBox="0 0 240 120" style="background: white; border-radius: 8px; padding: 10px; border: 1px solid #e2e8f0;">
                    <line x1="30" y1="15" x2="220" y2="15" stroke="#f1f5f9" stroke-width="1" />
                    <line x1="30" y1="50" x2="220" y2="50" stroke="#f1f5f9" stroke-width="1" />
                    <line x1="30" y1="85" x2="220" y2="85" stroke="#f1f5f9" stroke-width="1" />
                    <line x1="30" y1="100" x2="220" y2="100" stroke="#cbd5e1" stroke-width="2" />
                    <rect x="50" y="60" width="30" height="40" rx="3" fill="#94a3b8" />
                    <rect x="130" y="25" width="30" height="75" rx="3" fill="#4f46e5" />
                    <text x="65" y="112" font-family="'Inter', sans-serif" font-size="8" fill="#475569" text-anchor="middle">Outsourced</text>
                    <text x="145" y="112" font-family="'Inter', sans-serif" font-size="8" fill="#475569" text-anchor="middle">Internalized</text>
                    <text x="65" y="52" font-family="'Inter', sans-serif" font-size="8" fill="#64748b" text-anchor="middle">R$4.5M</text>
                    <text x="145" y="18" font-family="'Inter', sans-serif" font-size="8" fill="#4f46e5" font-weight="bold" text-anchor="middle">R$14.8M</text>
                  </svg>
                  <!-- Line Chart -->
                  <svg width="240" height="120" viewBox="0 0 240 120" style="background: white; border-radius: 8px; padding: 10px; border: 1px solid #e2e8f0;">
                    <line x1="30" y1="15" x2="220" y2="15" stroke="#f1f5f9" stroke-width="1" />
                    <line x1="30" y1="60" x2="220" y2="60" stroke="#cbd5e1" stroke-width="1" />
                    <line x1="30" y1="105" x2="220" y2="105" stroke="#f1f5f9" stroke-width="1" />
                    <path d="M 50 90 L 125 55 L 200 25" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" />
                    <circle cx="50" cy="90" r="4.5" fill="#10b981" />
                    <circle cx="125" cy="55" r="4.5" fill="#10b981" />
                    <circle cx="200" cy="25" r="4.5" fill="#10b981" />
                    <text x="50" y="102" font-family="'Inter', sans-serif" font-size="8" fill="#ef4444" text-anchor="middle">-R$2.5K</text>
                    <text x="200" y="16" font-family="'Inter', sans-serif" font-size="8" fill="#10b981" font-weight="bold" text-anchor="middle">+R$9.9K</text>
                    <text x="50" y="114" font-family="'Inter', sans-serif" font-size="8" fill="#475569" text-anchor="middle">Year 1</text>
                    <text x="200" y="114" font-family="'Inter', sans-serif" font-size="8" fill="#475569" text-anchor="middle">Year 3</text>
                  </svg>
                </div>
              </div>

              <div class="pdf-content">${compiledHTML}</div>
              <script>
                window.onload = function() {
                  setTimeout(function() {
                    window.print();
                  }, 500);
                }
              </script>
            </body>
          </html>
        `);
        printWindow.document.close();
      }
      return;
    } else if (outputFormat === "docx") {
      const compiledHTML = parseMarkdownToHTML(content);
      const wordDocument = `
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
          <head>
            <title>${topic}</title>
            <style>
              body { font-family: Arial, sans-serif; padding: 40px; color: #1e293b; line-height: 1.6; }
              h1 { color: #1e1b4b; font-size: 24px; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }
              h2 { color: #4338ca; font-size: 18px; margin-top: 24px; }
              h3 { color: #0f172a; font-size: 14px; margin-top: 18px; }
              p { margin-bottom: 12px; text-align: justify; }
              table { width: 100%; border-collapse: collapse; margin-top: 20px; }
              th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: left; }
              th { background-color: #f1f5f9; }
            </style>
          </head>
          <body>
            <h1>${topic}</h1>
            <p><strong>Generated on:</strong> ${new Date().toLocaleDateString()}</p>
            <div>${compiledHTML}</div>
          </body>
        </html>
      `;
      const blob = new Blob([wordDocument], { type: "application/msword" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Report_${topic.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.doc`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      return;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Report_${topic.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">Report Generation</h1>
        <p className="text-slate-400">Synthesize deep-dive reports across your entire document knowledge base.</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* Main Configuration */}
        <div className="space-y-6">
          <div className="rounded-[2.5rem] border border-white/10 bg-slate-900/40 p-8 backdrop-blur-xl shadow-2xl">
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Report Topic</label>
                <input 
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Q1 Financial Performance"
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-6 py-4 text-white placeholder-slate-600 focus:border-indigo-500/50 focus:outline-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Research Query</label>
                <textarea 
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={4}
                  placeholder="What specifically should the report cover? e.g. Analyze revenue growth, expense anomalies, and risk factors."
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-6 py-4 text-white placeholder-slate-600 focus:border-indigo-500/50 focus:outline-none resize-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2 col-span-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Report Type</label>
                  <select 
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-white focus:outline-none focus:border-indigo-500/50"
                  >
                    <option value="general">General Audit</option>
                    <option value="financial">Financial Analysis</option>
                    <option value="legal">Legal Review</option>
                    <option value="strategic">Strategic SWOT</option>
                  </select>
                </div>
                
                <div className="space-y-2 col-span-1 md:col-span-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Output Format</label>
                  <div className="grid grid-cols-4 sm:grid-cols-7 gap-1 rounded-2xl bg-slate-950/50 p-1 border border-white/5">
                    {[
                      { id: "markdown", label: "MD", icon: FileText },
                      { id: "table", label: "CSV", icon: TableIcon },
                      { id: "json", label: "JSON", icon: Code },
                      { id: "pdf", label: "PDF", icon: FileText },
                      { id: "docx", label: "Word", icon: FileText },
                      { id: "pptx", label: "PPT", icon: FileSpreadsheet },
                      { id: "excel", label: "Excel", icon: FileSpreadsheet }
                    ].map(f => {
                      const Icon = f.icon;
                      return (
                        <button 
                          key={f.id}
                          onClick={() => setOutputFormat(f.id as any)}
                          className={`flex flex-col items-center justify-center gap-1 rounded-xl py-2 text-[10px] font-bold transition ${outputFormat === f.id ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'}`}
                        >
                          <Icon className="h-4 w-4" />
                          {f.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <button 
                onClick={handleGenerate}
                disabled={isGenerating || !topic.trim() || !query.trim()}
                className="w-full flex items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 py-4 text-lg font-bold text-white shadow-xl shadow-indigo-500/20 transition hover:scale-[1.02] hover:brightness-110 disabled:opacity-50 disabled:hover:scale-100"
              >
                {isGenerating ? <Loader2 className="h-6 w-6 animate-spin" /> : <Sparkles className="h-6 w-6" />}
                Generate Report
              </button>
            </div>
          </div>

          {/* Result Area */}
          {result && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 space-y-6">
              <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">Report Ready</h2>
                    <p className="text-xs text-slate-500">Generated using {result.model_used || 'AI Engine'}</p>
                  </div>
                </div>
                <button 
                  onClick={downloadReport}
                  className="flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm font-bold text-white transition hover:bg-white/10"
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
              </div>

              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-8 backdrop-blur-xl overflow-x-auto">
                <div className="prose prose-invert max-w-none prose-sm prose-headings:text-white prose-p:text-slate-300 prose-strong:text-indigo-400 prose-ul:text-slate-400">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {outputFormat === "json" && !result.report.startsWith("```") 
                      ? `\`\`\`json\n${result.report}\n\`\`\`` 
                      : result.report}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4 flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <p className="text-sm text-red-200">{error}</p>
            </div>
          )}
        </div>

        {/* Sidebar: Settings */}
        <div className="space-y-6">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
            <div className="flex items-center gap-2 mb-6">
              <Settings2 className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Engine Settings</h3>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">AI Engine</label>
                <select 
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-950/50 p-3 text-xs text-white focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="openai">OpenAI (GPT-4)</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                  <option value="bedrock">AWS Bedrock</option>
                  <option value="custom">Custom Engine</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Model Choice</label>
                <select 
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-950/50 p-3 text-xs text-white focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="auto">Auto-Select (Optimized)</option>
                  {availableModels.map(m => (
                    <option key={m.model_id} value={m.model_id}>{m.label}</option>
                  ))}
                  {provider === "custom" && <option value="custom">Custom Model ID</option>}
                </select>
              </div>

              {model === "custom" && (
                <div className="space-y-2 animate-in slide-in-from-top-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-indigo-400">Custom Model ID</label>
                  <input 
                    type="text"
                    value={customModelId}
                    onChange={(e) => setCustomModelId(e.target.value)}
                    placeholder="e.g. meta-llama/Llama-2-70b"
                    className="w-full rounded-xl border border-indigo-500/30 bg-indigo-500/5 px-3 py-2 text-sm text-indigo-200 placeholder-indigo-500/50 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              )}

              <div className="rounded-2xl bg-indigo-500/5 border border-indigo-500/10 p-4">
                <p className="text-[10px] text-indigo-300 leading-relaxed">
                  <strong>Pro Tip:</strong> Use "Table" format for financial data and "Markdown" for executive summaries.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
