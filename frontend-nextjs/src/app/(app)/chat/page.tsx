"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { ArrowUp, Settings2, X } from "lucide-react";
import {
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

export default function ChatPage() {
  const { token } = useAuth();
  const {
    selectedModel,
    setSelectedModel,
    selectedCategory,
    setSelectedCategory,
    selectedPromptTemplate,
    setSelectedPromptTemplate,
    openaiApiKey,
    setOpenaiApiKey,
    anthropicApiKey,
    setAnthropicApiKey,
    geminiApiKey,
    setGeminiApiKey,
  } = useAppPreferences();

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

  useEffect(() => {
    getModels(token ?? undefined)
      .then((res) => setModels(["auto", ...res.models.filter((m) => m !== "auto")]))
      .catch(() => setModels(["auto"]));

    listPrompts(token ?? undefined)
      .then((res) => setPrompts(res.prompts))
      .catch(() => setPrompts([]));
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
    const MAX_POLLS = 120; // ~3 minutes
    const MAX_STAGNANT_POLLS = 20; // stop if processing count doesn't move

    const poll = async () => {
      try {
        const status = await getBatchStatus(uploadSummary.batch_id, token ?? undefined);
        if (cancelled) return;
        setUploadStatus(status);
        const completed = status.processing === 0 || status.ready + status.failed >= status.total;
        if (completed) {
          return;
        }

        pollCount += 1;
        if (status.processing === lastProcessing) {
          sameProcessingCount += 1;
        } else {
          sameProcessingCount = 0;
          lastProcessing = status.processing;
        }

        if (pollCount >= MAX_POLLS || sameProcessingCount >= MAX_STAGNANT_POLLS) {
          return;
        }

        if (status.processing > 0) {
          timer = window.setTimeout(poll, 1500);
        }
      } catch {
        // no-op, polling can transiently fail
        pollCount += 1;
        if (pollCount < MAX_POLLS) {
          timer = window.setTimeout(poll, 2000);
        }
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
    if (!uploadFiles.length) {
      setError("Select file(s) before uploading.");
      return;
    }
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
          model: selectedModel || "auto",
          category: selectedCategory || null,
          prompt_template: selectedPromptTemplate || undefined,
          openai_api_key: openaiApiKey || null,
          anthropic_api_key: anthropicApiKey || null,
          gemini_api_key: geminiApiKey || null,
          session_id: sessionId || undefined,
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
        { role: "assistant", content: "Failed to get response. Please try again." },
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

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-white">Chat</h2>
        <p className="text-sm text-slate-300">
          Streamlit core controls added: model selection, provider keys, category, and prompt template.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[300px_1fr]">
        <aside className="xl:sticky xl:top-24 xl:h-[calc(100dvh-7.5rem)] xl:self-start">
          <div className="flex h-full flex-col rounded-xl border border-white/15 bg-white/5">
            <div className="border-b border-white/10 p-4">
              <h3 className="text-sm font-semibold text-white">Conversation History</h3>
              <p className="mt-1 text-xs text-slate-300">Old chats on top, new chat at bottom.</p>
            </div>

            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
              {history.map((conv) => (
                <button
                  key={conv.session_id}
                  onClick={() => openConversation(conv.session_id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left transition ${
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
              ))}
              {!history.length && (
                <p className="text-xs text-slate-400">
                  {isHistoryLoading ? "Loading history..." : "No previous chats yet."}
                </p>
              )}
            </div>

            <div className="border-t border-white/10 p-3">
              <button
                type="button"
                onClick={() => {
                  setMessages([]);
                  setSessionId(null);
                }}
                className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 py-2 text-sm font-medium text-white hover:brightness-110"
              >
                + New Chat
              </button>
            </div>
          </div>
        </aside>

        <div className="flex min-h-0 flex-col gap-4 xl:h-[calc(100dvh-8.5rem)]">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/15 bg-white/5 p-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                Model: {selectedModel || "auto"}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                Category: {selectedCategory || "general"}
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

                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setControlTab("upload")}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                      controlTab === "upload"
                        ? "border border-cyan-300/40 bg-cyan-500/20 text-cyan-100"
                        : "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                    }`}
                  >
                    Upload Documents
                  </button>
                  <button
                    type="button"
                    onClick={() => setControlTab("query")}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                      controlTab === "query"
                        ? "border border-cyan-300/40 bg-cyan-500/20 text-cyan-100"
                        : "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                    }`}
                  >
                    Query Controls
                  </button>
                  <button
                    type="button"
                    onClick={() => setControlTab("keys")}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                      controlTab === "keys"
                        ? "border border-cyan-300/40 bg-cyan-500/20 text-cyan-100"
                        : "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                    }`}
                  >
                    Provider API Keys
                  </button>
                </div>

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
                      {isUploading ? "Uploading..." : "Upload to Knowledge Base"}
                    </button>
                    {!!uploadFiles.length && (
                      <p className="text-xs text-slate-300">{uploadFiles.length} file(s) selected</p>
                    )}
                    {uploadSummary && (
                      <p className="text-xs text-cyan-100">
                        Submitted: accepted {uploadSummary.accepted}, duplicates{" "}
                        {uploadSummary.duplicates}, rejected {uploadSummary.rejected}
                      </p>
                    )}
                    {uploadStatus && (
                      <p className="text-xs text-slate-300">
                        Processing: ready {uploadStatus.ready}, processing {uploadStatus.processing},
                        failed {uploadStatus.failed}
                      </p>
                    )}
                  </div>
                )}

                {controlTab === "query" && (
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-white">Query Controls</h4>
                    <label className="block text-xs text-slate-300">
                      Model
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      >
                        {models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                      </select>
                    </label>

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
                          <option key={prompt.id} value={prompt.template}>
                            {prompt.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}

                {controlTab === "keys" && (
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-white">Provider API Keys (Optional)</h4>
                    <label className="block text-xs text-slate-300">
                      OpenAI API Key
                      <input
                        type="password"
                        value={openaiApiKey}
                        onChange={(e) => setOpenaiApiKey(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      />
                    </label>
                    <label className="block text-xs text-slate-300">
                      Anthropic API Key
                      <input
                        type="password"
                        value={anthropicApiKey}
                        onChange={(e) => setAnthropicApiKey(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      />
                    </label>
                    <label className="block text-xs text-slate-300">
                      Gemini API Key
                      <input
                        type="password"
                        value={geminiApiKey}
                        onChange={(e) => setGeminiApiKey(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
                      />
                    </label>
                  </div>
                )}
              </div>
            </div>
          )}

          <article className="min-h-[260px] flex-1 overflow-y-auto rounded-xl border border-white/15 bg-white/5 p-5 max-h-[55dvh] xl:max-h-none">
            {!!messages.length ? (
              <div className="space-y-3">
                {messages.map((msg, idx) => (
                  <div
                    key={`${msg.role}-${idx}`}
                    className={`rounded-lg border p-3 ${
                      msg.role === "user"
                        ? "ml-8 border-cyan-300/30 bg-cyan-500/10"
                        : "mr-8 border-indigo-300/25 bg-indigo-500/10"
                    }`}
                  >
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-300">
                      {msg.role === "user" ? "You" : "Assistant"}
                    </p>
                    <p className="whitespace-pre-wrap text-sm text-slate-100">{msg.content}</p>
                    {!!msg.sources?.length && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                          Sources
                        </p>
                        {msg.sources.map((source, sourceIdx) => (
                          <div
                            key={`${source.title || "source"}-${sourceIdx}`}
                            className="rounded-md border border-white/10 bg-white/5 p-2"
                          >
                            <p className="text-xs font-medium text-cyan-100">
                              {source.title || `Source ${sourceIdx + 1}`}
                            </p>
                            <p className="mt-1 text-xs text-slate-300">
                              {source.excerpt || "No excerpt available."}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {isLoading && (
                  <div className="mr-8 rounded-lg border border-indigo-300/25 bg-indigo-500/10 p-3">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-300">
                      Assistant
                    </p>
                    <div className="flex items-center gap-2 text-sm text-slate-100">
                      <span>Thinking</span>
                      <span className="inline-flex gap-1">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-200 [animation-delay:0ms]" />
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-200 [animation-delay:200ms]" />
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-200 [animation-delay:400ms]" />
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="grid h-full place-items-center rounded-xl border border-dashed border-white/20 bg-white/5 p-10 text-center">
                <p className="text-sm text-slate-300">
                  Ask a question below. Use Chat Settings for uploads, model, and API keys.
                </p>
              </div>
            )}
          </article>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}

          <form
            onSubmit={onSubmit}
            className="flex items-end gap-2 rounded-2xl border border-white/15 bg-white/8 p-3 shadow-xl shadow-black/20 backdrop-blur"
          >
            <textarea
              rows={1}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="max-h-32 min-h-[40px] w-full resize-y border-0 bg-transparent px-2 py-2 text-base text-white outline-none placeholder:text-slate-400"
              placeholder="Ask anything"
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

