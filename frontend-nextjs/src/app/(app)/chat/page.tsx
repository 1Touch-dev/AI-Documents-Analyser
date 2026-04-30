"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { ArrowUp, Check, Clipboard, Settings2, Trash2, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  deleteConversation,
  detectCurrency,
  getConversation,
  getBatchStatus,
  getModels,
  listConversations,
  listPrompts,
  queryDocuments,
  type BatchStatusResponse,
  type ConversationItem,
  type PromptItem,
  type UploadBatchResponse,
  uploadBatch,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { useAppPreferences } from "@/contexts/app-preferences-context";

// ── Currency helpers ──────────────────────────────────────────────────────────
const CURRENCY_NAMES: Record<string, string> = {
  BRL: "Brazilian Real", USD: "US Dollar", CAD: "Canadian Dollar",
  MXN: "Mexican Peso", ARS: "Argentine Peso", CLP: "Chilean Peso",
  COP: "Colombian Peso", PEN: "Peruvian Sol",
  EUR: "Euro", GBP: "British Pound", CHF: "Swiss Franc",
  NOK: "Norwegian Krone", SEK: "Swedish Krona", DKK: "Danish Krone",
  PLN: "Polish Złoty", CZK: "Czech Koruna", HUF: "Hungarian Forint",
  RON: "Romanian Leu", TRY: "Turkish Lira", RUB: "Russian Ruble",
  UAH: "Ukrainian Hryvnia",
  JPY: "Japanese Yen", CNY: "Chinese Yuan", INR: "Indian Rupee",
  KRW: "South Korean Won", SGD: "Singapore Dollar", HKD: "Hong Kong Dollar",
  TWD: "Taiwan Dollar", THB: "Thai Baht", IDR: "Indonesian Rupiah",
  MYR: "Malaysian Ringgit", PHP: "Philippine Peso", VND: "Vietnamese Dong",
  AUD: "Australian Dollar", NZD: "New Zealand Dollar",
  AED: "UAE Dirham", SAR: "Saudi Riyal", QAR: "Qatari Riyal",
  ILS: "Israeli Shekel", EGP: "Egyptian Pound", ZAR: "South African Rand",
  NGN: "Nigerian Naira", KES: "Kenyan Shilling",
  PKR: "Pakistani Rupee", BDT: "Bangladeshi Taka",
};

// ── Currency list ─────────────────────────────────────────────────────────────
// First entry is "Default" — the native document currency (auto-detected).
// Remaining entries are grouped by region for easy scanning.
const CURRENCY_OPTIONS: { code: string; label: string }[] = [
  { code: "BRL", label: "Default (Brazilian Real — BRL)" },
  // ── Americas ──────────────────────────────────────────────
  { code: "USD", label: "US Dollar (USD)" },
  { code: "CAD", label: "Canadian Dollar (CAD)" },
  { code: "MXN", label: "Mexican Peso (MXN)" },
  { code: "ARS", label: "Argentine Peso (ARS)" },
  { code: "CLP", label: "Chilean Peso (CLP)" },
  { code: "COP", label: "Colombian Peso (COP)" },
  { code: "PEN", label: "Peruvian Sol (PEN)" },
  // ── Europe ────────────────────────────────────────────────
  { code: "EUR", label: "Euro (EUR)" },
  { code: "GBP", label: "British Pound (GBP)" },
  { code: "CHF", label: "Swiss Franc (CHF)" },
  { code: "NOK", label: "Norwegian Krone (NOK)" },
  { code: "SEK", label: "Swedish Krona (SEK)" },
  { code: "DKK", label: "Danish Krone (DKK)" },
  { code: "PLN", label: "Polish Złoty (PLN)" },
  { code: "CZK", label: "Czech Koruna (CZK)" },
  { code: "HUF", label: "Hungarian Forint (HUF)" },
  { code: "RON", label: "Romanian Leu (RON)" },
  { code: "TRY", label: "Turkish Lira (TRY)" },
  { code: "RUB", label: "Russian Ruble (RUB)" },
  { code: "UAH", label: "Ukrainian Hryvnia (UAH)" },
  // ── Asia-Pacific ──────────────────────────────────────────
  { code: "JPY", label: "Japanese Yen (JPY)" },
  { code: "CNY", label: "Chinese Yuan (CNY)" },
  { code: "INR", label: "Indian Rupee (INR)" },
  { code: "KRW", label: "South Korean Won (KRW)" },
  { code: "SGD", label: "Singapore Dollar (SGD)" },
  { code: "HKD", label: "Hong Kong Dollar (HKD)" },
  { code: "TWD", label: "Taiwan Dollar (TWD)" },
  { code: "THB", label: "Thai Baht (THB)" },
  { code: "IDR", label: "Indonesian Rupiah (IDR)" },
  { code: "MYR", label: "Malaysian Ringgit (MYR)" },
  { code: "PHP", label: "Philippine Peso (PHP)" },
  { code: "VND", label: "Vietnamese Dong (VND)" },
  { code: "AUD", label: "Australian Dollar (AUD)" },
  { code: "NZD", label: "New Zealand Dollar (NZD)" },
  // ── Middle East / Africa ──────────────────────────────────
  { code: "AED", label: "UAE Dirham (AED)" },
  { code: "SAR", label: "Saudi Riyal (SAR)" },
  { code: "QAR", label: "Qatari Riyal (QAR)" },
  { code: "ILS", label: "Israeli Shekel (ILS)" },
  { code: "EGP", label: "Egyptian Pound (EGP)" },
  { code: "ZAR", label: "South African Rand (ZAR)" },
  { code: "NGN", label: "Nigerian Naira (NGN)" },
  { code: "KES", label: "Kenyan Shilling (KES)" },
  // ── South Asia ────────────────────────────────────────────
  { code: "PKR", label: "Pakistani Rupee (PKR)" },
  { code: "BDT", label: "Bangladeshi Taka (BDT)" },
];

// ── Markdown component map ────────────────────────────────────────────────────
// Applied to every assistant message so the GPT markdown renders properly.
const mdComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-base font-bold text-white mt-3 mb-1">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-sm font-bold text-white mt-3 mb-1">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-sm font-semibold text-slate-100 mt-2 mb-1">{children}</h3>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="text-sm text-slate-100 leading-relaxed mb-2 last:mb-0">{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-white">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="italic text-slate-200">{children}</em>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="list-disc list-outside ml-4 space-y-1 my-2 text-slate-100">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="list-decimal list-outside ml-4 space-y-1 my-2 text-slate-100">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="text-sm text-slate-100 leading-relaxed">{children}</li>
  ),
  code: ({ children, className }: { children?: React.ReactNode; className?: string }) => {
    const isBlock = className?.includes("language-");
    return isBlock ? (
      <code className="block bg-slate-900/70 rounded p-3 text-xs font-mono text-cyan-200 overflow-x-auto my-2 whitespace-pre">
        {children}
      </code>
    ) : (
      <code className="bg-white/10 rounded px-1.5 py-0.5 text-xs font-mono text-cyan-300">
        {children}
      </code>
    );
  },
  pre: ({ children }: { children?: React.ReactNode }) => (
    <pre className="bg-slate-900/70 rounded-lg my-2 overflow-x-auto">{children}</pre>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-2 border-cyan-500/60 pl-3 my-2 text-slate-300 italic">
      {children}
    </blockquote>
  ),
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-cyan-300 underline underline-offset-2 hover:text-cyan-200"
    >
      {children}
    </a>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto my-2">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => (
    <thead className="bg-white/10">{children}</thead>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border border-white/20 px-3 py-1.5 text-left font-semibold text-slate-100">
      {children}
    </th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border border-white/15 px-3 py-1.5 text-slate-200">{children}</td>
  ),
  hr: () => <hr className="border-white/15 my-3" />,
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const { token } = useAuth();
  const {
    selectedProvider,
    setSelectedProvider,
    selectedModel,
    setSelectedModel,
    bedrockCustomModel,
    setBedrockCustomModel,
    selectedCategory,
    setSelectedCategory,
    selectedPromptTemplate,
    setSelectedPromptTemplate,
    openaiApiKey,
    setOpenaiApiKey,
    translateToEnglish,
    setTranslateToEnglish,
    targetCurrency,
    setTargetCurrency,
  } = useAppPreferences();

  // Resolve the effective model sent to the backend
  const effectiveModel =
    selectedProvider === "bedrock" && bedrockCustomModel.trim()
      ? bedrockCustomModel.trim()
      : selectedModel || "auto";

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<
    Array<{
      role: "user" | "assistant";
      content: string;
      sources?: Array<{ title?: string; excerpt?: string }>;
    }>
  >([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<string[]>(["auto"]);
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadSummary, setUploadSummary] = useState<UploadBatchResponse | null>(null);
  const [uploadStatus, setUploadStatus] = useState<BatchStatusResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [history, setHistory] = useState<ConversationItem[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [controlTab, setControlTab] = useState<"upload" | "query" | "keys">("query");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const copyTimerRef = useRef<number | undefined>(undefined);
  const [detectedCurrency, setDetectedCurrency] = useState<string>("BRL");
  const [detectedCurrencyConfidence, setDetectedCurrencyConfidence] = useState<string>("none");

  useEffect(() => {
    getModels(token ?? undefined)
      .then((res) => setModels(["auto", ...res.models.filter((m) => m !== "auto")]))
      .catch(() => setModels(["auto"]));

    listPrompts(token ?? undefined)
      .then((res) => setPrompts(res.prompts))
      .catch(() => setPrompts([]));

    // Detect dominant currency in indexed documents (heuristic, no LLM)
    detectCurrency(token ?? undefined)
      .then((res) => {
        if (res.currency && res.confidence !== "none") {
          setDetectedCurrency(res.currency);
          setDetectedCurrencyConfidence(res.confidence);
          // Auto-apply detected currency if user still has the old BRL default
          if (targetCurrency === "BRL" && res.currency !== "BRL") {
            setTargetCurrency(res.currency);
          }
        }
      })
      .catch(() => {/* keep BRL default silently */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function refreshHistory() {
    if (!token) return;
    setIsHistoryLoading(true);
    try {
      const response = await listConversations(token ?? undefined);
      setHistory(response.conversations);
    } finally {
      setIsHistoryLoading(false);
    }
  }

  useEffect(() => {
    refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!uploadSummary?.batch_id || !token) return;

    let timer: number | undefined;
    let cancelled = false;
    let pollCount = 0;
    let sameProcessingCount = 0;
    let lastProcessing = -1;
    const MAX_POLLS = 120;
    const MAX_STAGNANT_POLLS = 20;

    const poll = async () => {
      try {
        const status = await getBatchStatus(uploadSummary.batch_id, token ?? undefined);
        if (cancelled) return;
        setUploadStatus(status);
        const completed = status.processing === 0 || status.ready + status.failed >= status.total;
        if (completed) return;

        pollCount += 1;
        if (status.processing === lastProcessing) {
          sameProcessingCount += 1;
        } else {
          sameProcessingCount = 0;
          lastProcessing = status.processing;
        }
        if (pollCount >= MAX_POLLS || sameProcessingCount >= MAX_STAGNANT_POLLS) return;
        if (status.processing > 0) timer = window.setTimeout(poll, 800);
      } catch {
        pollCount += 1;
        if (pollCount < MAX_POLLS) timer = window.setTimeout(poll, 1500);
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [uploadSummary?.batch_id, token]);

  function onSelectUploadFiles(event: ChangeEvent<HTMLInputElement>) {
    setUploadFiles(Array.from(event.target.files || []));
  }

  async function onUploadFromChat() {
    if (!uploadFiles.length) { setError("Select file(s) before uploading."); return; }
    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadBatch(uploadFiles, selectedCategory || "general", token ?? undefined);
      setUploadSummary(result);
      setUploadFiles([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    const currentQuestion = question.trim();
    setQuestion("");
    setError(null);
    setIsLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: currentQuestion }]);
    try {
      const result = await queryDocuments(
        {
          question: currentQuestion,
          model: effectiveModel,
          provider: selectedProvider,
          category: selectedCategory || null,
          prompt_template: selectedPromptTemplate || undefined,
          openai_api_key: openaiApiKey || null,
          session_id: sessionId || undefined,
          translate_to_english: translateToEnglish,
          target_currency: targetCurrency,
        },
        token ?? undefined
      );
      setSessionId(result.session_id || null);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer, sources: result.sources ?? [] },
      ]);
      await refreshHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to query documents.");
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Failed to get a response. Please try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  async function openConversation(sessionIdToLoad: string) {
    if (!token) return;
    setError(null);
    try {
      const conversation = await getConversation(sessionIdToLoad, token ?? undefined);
      setSessionId(conversation.session_id);
      setMessages(
        (conversation.messages || []).map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources || [],
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load conversation.");
    }
  }

  // Dynamic first dropdown option label based on detected document currency
  const defaultOptionLabel =
    detectedCurrencyConfidence !== "none"
      ? `Default (${CURRENCY_NAMES[detectedCurrency] ?? detectedCurrency} — ${detectedCurrency}, auto-detected)`
      : `Default (Brazilian Real — BRL)`;

  // Badge label for the status bar
  const currencyLabel =
    targetCurrency === detectedCurrency
      ? `Default (${detectedCurrency})`
      : targetCurrency;

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-white">Chat</h2>
        <p className="text-sm text-slate-300">
          Ask questions across your uploaded documents. Responses are rendered with full formatting.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[300px_1fr]">
        {/* ── Conversation history sidebar ─────────────────────────────── */}
        <aside className="xl:sticky xl:top-24 xl:h-[calc(100dvh-7.5rem)] xl:self-start">
          <div className="flex h-full flex-col rounded-xl border border-white/15 bg-white/5">
            <div className="border-b border-white/10 p-4">
              <h3 className="text-sm font-semibold text-white">Conversation History</h3>
              <p className="mt-1 text-xs text-slate-300">Click a past session to resume it.</p>
            </div>

            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
              {history.map((conv) => (
                <div key={conv.session_id} className="group flex items-stretch gap-1">
                  <button
                    onClick={() => openConversation(conv.session_id)}
                    className={`min-w-0 flex-1 rounded-lg border px-3 py-2 text-left transition ${
                      sessionId === conv.session_id
                        ? "border-cyan-300/45 bg-cyan-500/15"
                        : "border-white/10 bg-white/5 hover:bg-white/10"
                    }`}
                  >
                    <p className="truncate text-xs font-semibold text-slate-100">
                      {conv.title || "Untitled chat"}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {conv.message_count} messages
                      {conv.category ? ` · ${conv.category}` : ""}
                    </p>
                  </button>
                  <button
                    type="button"
                    title="Delete conversation"
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (!token) return;
                      try {
                        await deleteConversation(conv.session_id, token);
                        if (sessionId === conv.session_id) {
                          setMessages([]);
                          setSessionId(null);
                        }
                        await refreshHistory();
                      } catch {
                        /* silently ignore */
                      }
                    }}
                    className="shrink-0 rounded-lg border border-white/10 bg-white/5 p-1.5 text-slate-400 opacity-0 transition hover:border-red-400/40 hover:bg-red-500/15 hover:text-red-300 group-hover:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {!history.length && (
                <p className="text-xs text-slate-400">
                  {isHistoryLoading ? "Loading history…" : "No previous chats yet."}
                </p>
              )}
            </div>

            <div className="border-t border-white/10 p-3">
              <button
                type="button"
                onClick={() => { setMessages([]); setSessionId(null); }}
                className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 py-2 text-sm font-medium text-white hover:brightness-110"
              >
                + New Chat
              </button>
            </div>
          </div>
        </aside>

        {/* ── Main chat area ───────────────────────────────────────────── */}
        <div className="flex min-h-0 flex-col gap-4 xl:h-[calc(100dvh-8.5rem)]">

          {/* Status bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/15 bg-white/5 p-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                {selectedProvider === "bedrock" ? "🌩️ Bedrock" : "☁️ OpenAI"}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                Model: {effectiveModel}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                Category: {selectedCategory || "general"}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                Translate: {translateToEnglish ? "On" : "Off"}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                Currency: {currencyLabel}
              </span>
              {!!uploadFiles.length && (
                <span className="rounded-full border border-cyan-300/30 bg-cyan-500/10 px-2.5 py-1 text-cyan-100">
                  {uploadFiles.length} file(s) selected
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => setIsSettingsOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-3 py-2 text-sm font-medium text-white hover:brightness-110"
            >
              <Settings2 className="h-4 w-4" />
              Chat Settings
            </button>
          </div>

          {/* Settings modal */}
          {isSettingsOpen && (
            <div
              className="fixed inset-0 z-50 grid place-items-center bg-slate-950/70 p-4 backdrop-blur-sm"
              onClick={() => setIsSettingsOpen(false)}
            >
              <div
                className="w-full max-w-2xl rounded-2xl border border-white/15 bg-slate-950/95 p-5 shadow-2xl shadow-black/50"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-base font-semibold text-white">Chat Settings</h3>
                  <button
                    type="button"
                    onClick={() => setIsSettingsOpen(false)}
                    className="rounded-md border border-white/15 bg-white/5 p-1.5 text-slate-200 hover:bg-white/10"
                    title="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {/* Tab switcher */}
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  {(["upload", "query", "keys"] as const).map((tab) => (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setControlTab(tab)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                        controlTab === tab
                          ? "border border-cyan-300/40 bg-cyan-500/20 text-cyan-100"
                          : "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                      }`}
                    >
                      {tab === "upload" ? "Upload Documents"
                        : tab === "query" ? "Query Controls"
                        : "OpenAI API"}
                    </button>
                  ))}
                </div>

                {/* Upload tab */}
                {controlTab === "upload" && (
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-white">Upload Documents (In Chat)</h4>
                    <input
                      type="file"
                      multiple
                      onChange={onSelectUploadFiles}
                      className="w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                    />
                    <button
                      type="button"
                      onClick={onUploadFromChat}
                      disabled={isUploading}
                      className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                    >
                      {isUploading ? "Uploading…" : "Upload to Knowledge Base"}
                    </button>
                    {!!uploadFiles.length && (
                      <p className="text-xs text-slate-300">{uploadFiles.length} file(s) selected</p>
                    )}
                    {uploadSummary && (
                      <p className="text-xs text-cyan-100">
                        Submitted — accepted: {uploadSummary.accepted}, duplicates: {uploadSummary.duplicates}, rejected: {uploadSummary.rejected}
                      </p>
                    )}
                    {uploadStatus && (
                      <p className="text-xs text-slate-300">
                        Processing — ready: {uploadStatus.ready}, processing: {uploadStatus.processing}, failed: {uploadStatus.failed}
                      </p>
                    )}
                  </div>
                )}

                {/* Query controls tab */}
                {controlTab === "query" && (
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-white">Query Controls</h4>

                    {/* Provider selector */}
                    <label className="block text-xs text-slate-300">
                      AI Provider
                      <select
                        value={selectedProvider}
                        onChange={(e) => {
                          setSelectedProvider(e.target.value);
                          setBedrockCustomModel("");
                          setSelectedModel(e.target.value === "bedrock" ? "amazon.nova-lite-v1:0" : "auto");
                        }}
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      >
                        <option value="openai">☁️  OpenAI  (GPT-4o / GPT-4.1)</option>
                        <option value="bedrock">🌩️  AWS Bedrock  (Claude · Nova · Llama · Mistral · Cohere)</option>
                      </select>
                    </label>

                    {/* Model selector — changes based on provider */}
                    {selectedProvider === "openai" ? (
                      <label className="block text-xs text-slate-300">
                        Model
                        <select
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                        >
                          {["auto", "gpt-4o", "gpt-4.1", "gpt-4.1-mini"].map((m) => (
                            <option key={m} value={m}>{m === "auto" ? "auto · smart routing (Recommended)" : m}</option>
                          ))}
                        </select>
                      </label>
                    ) : (
                      <>
                        <label className="block text-xs text-slate-300">
                          Bedrock Model
                          <select
                            value={selectedModel}
                            onChange={(e) => { setSelectedModel(e.target.value); setBedrockCustomModel(""); }}
                            className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                          >
                            <option value="amazon.nova-lite-v1:0">Nova Lite · Amazon (fast + multimodal)</option>
                            <option value="amazon.nova-micro-v1:0">Nova Micro · Amazon (fastest / cheapest)</option>
                            <option value="amazon.nova-pro-v1:0">Nova Pro · Amazon (highest quality)</option>
                            <option value="us.anthropic.claude-sonnet-4-5-20251203-v1:0">Claude Sonnet 4.6 · Anthropic (balanced)</option>
                            <option value="us.anthropic.claude-haiku-3-5-20241022-v1:0">Claude Haiku · Anthropic (fast)</option>
                            <option value="us.anthropic.claude-opus-4-5-20251101-v1:0">Claude Opus 4.6 · Anthropic (flagship)</option>
                            <option value="us.anthropic.claude-opus-4-7-20260416-v1:0">Claude Opus 4.7 · Anthropic (latest)</option>
                            <option value="us.meta.llama3-70b-instruct-v1:0">Llama 3 70B · Meta</option>
                            <option value="us.meta.llama3-8b-instruct-v1:0">Llama 3 8B · Meta</option>
                            <option value="mistral.mistral-large-2402-v1:0">Mistral Large · Mistral AI</option>
                            <option value="mistral.mixtral-8x7b-instruct-v0:1">Mixtral 8×7B · Mistral AI</option>
                            <option value="cohere.command-r-plus-v1:0">Command R+ · Cohere (RAG-optimised)</option>
                          </select>
                        </label>
                        <label className="block text-xs text-slate-300">
                          Custom Bedrock Model ID
                          <span className="ml-1 text-slate-500">(overrides dropdown — any model ID accepted)</span>
                          <input
                            type="text"
                            value={bedrockCustomModel}
                            onChange={(e) => setBedrockCustomModel(e.target.value)}
                            placeholder="e.g. us.anthropic.claude-opus-4-7-20260416-v1:0"
                            className="mt-1 w-full rounded-lg border border-cyan-500/30 bg-slate-950/60 px-3 py-2 text-sm text-cyan-100 placeholder-slate-500"
                          />
                          {bedrockCustomModel.trim() && (
                            <p className="mt-1 text-[11px] text-cyan-400">
                              ✓ Using custom model: {bedrockCustomModel.trim()}
                            </p>
                          )}
                        </label>
                      </>
                    )}

                    <label className="block text-xs text-slate-300">
                      Category
                      <input
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        placeholder="general"
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      />
                    </label>

                    <label className="block text-xs text-slate-300">
                      Prompt Template
                      <select
                        value={selectedPromptTemplate}
                        onChange={(e) => setSelectedPromptTemplate(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      >
                        <option value="">Default (built-in)</option>
                        {prompts.map((prompt) => (
                          <option key={prompt.id} value={prompt.template}>{prompt.name}</option>
                        ))}
                      </select>
                    </label>

                    {/* Translate toggle */}
                    <label className="flex items-center justify-between rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 cursor-pointer">
                      <span>Translate to English</span>
                      <input
                        type="checkbox"
                        checked={translateToEnglish}
                        onChange={(e) => setTranslateToEnglish(e.target.checked)}
                        className="h-4 w-4 accent-cyan-400"
                      />
                    </label>

                    {/* Currency selector — full list with Default (BRL) first */}
                    <label className="block text-xs text-slate-300">
                      Output Currency
                      <select
                        value={targetCurrency}
                        onChange={(e) => setTargetCurrency(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      >
                        {CURRENCY_OPTIONS.map(({ code, label }, idx) => (
                          <option key={code} value={idx === 0 ? detectedCurrency : code}>
                            {idx === 0 ? defaultOptionLabel : label}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1 text-[11px] text-slate-400">
                        Live rates via fawazahmed0 open-source API — updated hourly.
                      </p>
                    </label>
                  </div>
                )}

                {/* API key tab */}
                {controlTab === "keys" && (
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-white">OpenAI API Key</h4>
                    <p className="text-xs text-slate-300">
                      All generation uses GPT API (cloud models only — no local model required).
                      Paste your key here if the server has no global key configured.
                    </p>
                    <label className="block text-xs text-slate-300">
                      OpenAI API Key
                      <input
                        type="password"
                        value={openaiApiKey}
                        onChange={(e) => setOpenaiApiKey(e.target.value)}
                        placeholder="sk-…"
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      />
                    </label>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Message thread ───────────────────────────────────────── */}
          <article className="min-h-[260px] flex-1 overflow-y-auto rounded-xl border border-white/15 bg-white/5 p-5 max-h-[55dvh] xl:max-h-none">
            {!!messages.length ? (
              <div className="space-y-4">
                {messages.map((msg, idx) => (
                  <div
                    key={`${msg.role}-${idx}`}
                    className={`rounded-xl border p-4 ${
                      msg.role === "user"
                        ? "ml-8 border-cyan-300/30 bg-cyan-500/10"
                        : "mr-8 border-indigo-300/25 bg-indigo-500/10"
                    }`}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                        {msg.role === "user" ? "You" : "Assistant"}
                      </p>
                      {msg.role === "assistant" && (
                        <button
                          type="button"
                          title="Copy response"
                          onClick={() => {
                            navigator.clipboard.writeText(msg.content).then(() => {
                              setCopiedIdx(idx);
                              if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current);
                              copyTimerRef.current = window.setTimeout(() => setCopiedIdx(null), 2000);
                            });
                          }}
                          className="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-slate-400 transition hover:border-white/20 hover:bg-white/10 hover:text-slate-200"
                        >
                          {copiedIdx === idx ? (
                            <><Check className="h-3 w-3 text-green-400" /><span className="text-green-400">Copied</span></>
                          ) : (
                            <><Clipboard className="h-3 w-3" /><span>Copy</span></>
                          )}
                        </button>
                      )}
                    </div>

                    {/* User messages: plain text. Assistant: rendered markdown. */}
                    {msg.role === "user" ? (
                      <p className="whitespace-pre-wrap text-sm text-slate-100">{msg.content}</p>
                    ) : (
                      <div className="prose-invert max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={mdComponents}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}

                    {/* Source citations */}
                    {!!msg.sources?.length && (
                      <div className="mt-4 space-y-2">
                        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                          Sources
                        </p>
                        {msg.sources.map((source, sourceIdx) => (
                          <div
                            key={`${source.title || "source"}-${sourceIdx}`}
                            className="rounded-lg border border-white/10 bg-white/5 p-2.5"
                          >
                            <p className="text-xs font-semibold text-cyan-200">
                              [{sourceIdx + 1}] {source.title || `Source ${sourceIdx + 1}`}
                            </p>
                            <p className="mt-1 text-xs leading-relaxed text-slate-300">
                              {source.excerpt || "No excerpt available."}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {/* Thinking indicator */}
                {isLoading && (
                  <div className="mr-8 rounded-xl border border-indigo-300/25 bg-indigo-500/10 p-4">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">
                      Assistant
                    </p>
                    <div className="flex items-center gap-2 text-sm text-slate-300">
                      <span>Thinking</span>
                      <span className="inline-flex gap-1">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300 [animation-delay:0ms]" />
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300 [animation-delay:200ms]" />
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300 [animation-delay:400ms]" />
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="grid h-full place-items-center rounded-xl border border-dashed border-white/20 bg-white/5 p-10 text-center">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-200">Ask anything about your documents</p>
                  <p className="text-xs text-slate-400">
                    Use <strong className="text-slate-300">Chat Settings</strong> to choose model, currency, or upload new files.
                  </p>
                </div>
              </div>
            )}
          </article>

          {error && <p className="text-sm text-red-300">{error}</p>}

          {/* Input form */}
          <form
            onSubmit={onSubmit}
            className="flex items-end gap-2 rounded-2xl border border-white/15 bg-white/8 p-3 shadow-xl shadow-black/20 backdrop-blur"
          >
            <textarea
              rows={1}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!isLoading && question.trim()) onSubmit(e as unknown as FormEvent);
                }
              }}
              className="max-h-32 min-h-[40px] w-full resize-y border-0 bg-transparent px-2 py-2 text-base text-white outline-none placeholder:text-slate-400"
              placeholder="Ask anything — press Enter to send, Shift+Enter for new line"
            />
            <button
              disabled={isLoading || !question.trim()}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white text-slate-900 transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-white/50"
              title="Send"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
