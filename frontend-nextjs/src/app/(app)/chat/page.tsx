"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { 
  ArrowUp, 
  Check, 
  Clipboard, 
  Settings2, 
  Trash2, 
  X, 
  MessageSquare, 
  Plus, 
  Search, 
  Sparkles, 
  AlertCircle,
  UploadCloud,
  ChevronRight,
  Globe,
  Coins,
  Cpu,
  FileText as FileIcon,
  Loader2
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  deleteConversation,
  getConversation,
  listConversations,
  queryDocuments,
  getModels,
  listPrompts,
  uploadBatch,
  type ConversationItem,
  type PromptItem,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { useAppPreferences } from "@/contexts/app-preferences-context";

// ── Markdown component map ────────────────────────────────────────────────────
const mdComponents = {
  h1: ({ children }: any) => <h1 className="text-xl font-bold text-white mt-4 mb-2">{children}</h1>,
  h2: ({ children }: any) => <h2 className="text-lg font-bold text-white mt-3 mb-2">{children}</h2>,
  h3: ({ children }: any) => <h3 className="text-base font-semibold text-slate-100 mt-2 mb-1">{children}</h3>,
  p: ({ children }: any) => <p className="text-sm text-slate-300 leading-relaxed mb-4 last:mb-0">{children}</p>,
  ul: ({ children }: any) => <ul className="list-disc ml-6 space-y-2 mb-4 text-slate-300">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal ml-6 space-y-2 mb-4 text-slate-300">{children}</ol>,
  li: ({ children }: any) => <li className="text-sm leading-relaxed">{children}</li>,
  code: ({ children, className }: any) => {
    const isBlock = className?.includes("language-");
    return isBlock ? (
      <pre className="bg-slate-950/80 rounded-xl p-4 text-xs font-mono text-cyan-200 overflow-x-auto my-4 border border-white/5">
        <code>{children}</code>
      </pre>
    ) : (
      <code className="bg-white/10 rounded px-1.5 py-0.5 text-xs font-mono text-cyan-300">{children}</code>
    );
  },
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-4 border-indigo-500/50 pl-4 my-4 text-slate-400 italic bg-white/5 py-2 rounded-r-lg">
      {children}
    </blockquote>
  ),
  table: ({ children }: any) => (
    <div className="overflow-x-auto my-4 rounded-xl border border-white/10">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }: any) => <th className="bg-white/10 border border-white/10 px-4 py-2 text-left font-bold text-white">{children}</th>,
  td: ({ children }: any) => <td className="border border-white/10 px-4 py-2 text-slate-300">{children}</td>,
};

const CURRENCY_OPTIONS = [
  { code: "BRL", name: "Brazilian Real (Auto-Detected)" },
  { code: "USD", name: "US Dollar (USD)" },
  { code: "EUR", name: "Euro (EUR)" },
  { code: "GBP", name: "British Pound (GBP)" },
  { code: "JPY", name: "Japanese Yen (JPY)" },
  { code: "CAD", name: "Canadian Dollar (CAD)" },
  { code: "AUD", name: "Australian Dollar (AUD)" },
  { code: "CNY", name: "Chinese Yuan (CNY)" },
  { code: "INR", name: "Indian Rupee (INR)" },
  { code: "AED", name: "UAE Dirham (AED)" },
  { code: "CHF", name: "Swiss Franc (CHF)" }
];

export default function ChatPage() {
  const { token } = useAuth();
  const {
    selectedCategory,
    setSelectedCategory,
    translateToEnglish,
    setTranslateToEnglish,
    targetCurrency,
    setTargetCurrency,
  } = useAppPreferences();

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ConversationItem[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "advanced">("general");
  
  // Advanced Settings State (Restored)
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("auto");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<string>("");
  
  // Upload State (Restored)
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    refreshHistory();
    fetchAdvancedData();
  }, [token]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function fetchAdvancedData() {
    if (!token) return;
    try {
      const [modelsRes, promptsRes] = await Promise.all([
        getModels(token),
        listPrompts(token)
      ]);
      setAvailableModels(modelsRes.models || []);
      setPrompts(promptsRes.prompts);
    } catch (e) {}
  }

  useEffect(() => {
    if (token) {
      getModels(token).then(res => {
        setAvailableModels(res.models || []);
      }).catch(() => {});
    }
  }, [provider, token]);

  async function refreshHistory() {
    if (!token) return;
    try {
      const response = await listConversations(token ?? undefined);
      setHistory(response.conversations);
    } catch (e) {}
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || isLoading) return;
    
    const currentQuestion = question.trim();
    setQuestion("");
    setError(null);
    setIsLoading(true);
    
    const userMsg = { role: "user", content: currentQuestion };
    setMessages(prev => [...prev, userMsg]);

    try {
      const result = await queryDocuments({
        question: currentQuestion,
        model: model,
        provider: provider,
        category: selectedCategory === "All" ? null : selectedCategory,
        session_id: sessionId || undefined,
        translate_to_english: translateToEnglish,
        target_currency: targetCurrency,
        prompt_template: prompts.find(p => p.id === selectedPrompt)?.template || undefined,
      }, token ?? undefined);

      setSessionId(result.session_id || null);
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: result.answer, 
        sources: result.sources ?? [] 
      }]);
      refreshHistory();
    } catch (e) {
      setError("I encountered an issue processing that. Please try again.");
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "Sorry, I couldn't process your request at this time." 
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function onFileUpload(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (!files.length || !token) return;
    setUploadFiles(files);
    setIsUploading(true);
    try {
      await uploadBatch(files, selectedCategory === "All" ? "General" : selectedCategory, token);
      alert(`${files.length} documents uploaded successfully.`);
      setUploadFiles([]);
    } catch (e) {
      alert("Failed to upload documents.");
    } finally {
      setIsUploading(false);
    }
  }

  async function loadChat(id: string) {
    try {
      const chat = await getConversation(id, token ?? undefined);
      setSessionId(chat.session_id);
      setMessages(chat.messages.map(m => ({ role: m.role, content: m.content, sources: m.sources })));
    } catch (e) {
      setError("Failed to load conversation.");
    }
  }

  async function startNewChat() {
    setMessages([]);
    setSessionId(null);
    setQuestion("");
  }

  async function handleDeleteChat(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!token) return;
    try {
      await deleteConversation(id, token);
      if (sessionId === id) {
        startNewChat();
      }
      refreshHistory();
    } catch (e) {}
  }

  return (
    <div className="mx-auto max-w-7xl h-[calc(100vh-140px)] flex gap-8">
      {/* Sidebar: History */}
      <aside className="w-80 flex flex-col rounded-[2rem] border border-white/10 bg-white/5 backdrop-blur-xl overflow-hidden hidden xl:flex">
        <div className="p-6 border-b border-white/5">
          <button 
            onClick={startNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 py-3 text-sm font-bold text-white shadow-lg transition hover:scale-[1.02] hover:brightness-110"
          >
            <Plus className="h-4 w-4" />
            New Conversation
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <p className="px-2 mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">Recent Chats</p>
          {history.map(chat => (
            <div key={chat.session_id} className="group relative">
              <button
                onClick={() => loadChat(chat.session_id)}
                className={`flex w-full items-center gap-3 rounded-2xl p-3 text-left transition pr-10 ${sessionId === chat.session_id ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-400 hover:bg-white/5'}`}
              >
                <MessageSquare className="h-4 w-4 shrink-0" />
                <span className="truncate text-sm font-medium">{chat.title || "Untitled Chat"}</span>
              </button>
              <button 
                onClick={(e) => handleDeleteChat(chat.session_id, e)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-600 opacity-0 transition group-hover:opacity-100 hover:text-red-400"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col rounded-[2.5rem] border border-white/10 bg-slate-900/40 backdrop-blur-2xl overflow-hidden relative">
        {/* Chat Header */}
        <div className="flex items-center justify-between px-8 py-4 border-b border-white/5 bg-white/5">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-indigo-500/20 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">AI Business Assistant</h2>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">
                {targetCurrency !== 'BRL' ? `Currency: ${targetCurrency}` : 'Powered by your documents'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isLoading && <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />}
            <button 
              onClick={() => setIsSettingsOpen(true)}
              className="rounded-xl bg-white/5 p-2 text-slate-400 hover:bg-white/10 hover:text-white"
            >
              <Settings2 className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Message Thread */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
              <div className="h-20 w-20 rounded-full bg-white/5 flex items-center justify-center mb-6">
                <Search className="h-10 w-10 text-slate-500" />
              </div>
              <h3 className="text-xl font-bold text-white">How can I help you today?</h3>
              <p className="mt-2 text-sm max-w-sm text-slate-400">Ask questions about your business documents, financial reports, or contracts.</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] group relative rounded-3xl p-6 ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white/5 border border-white/10 rounded-tl-none'}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                    {msg.content}
                  </ReactMarkdown>
                  
                  {msg.role === 'assistant' && (
                    <button 
                      onClick={() => navigator.clipboard.writeText(msg.content)}
                      className="absolute top-4 right-4 p-2 rounded-lg bg-white/5 text-slate-500 opacity-0 transition group-hover:opacity-100 hover:bg-white/10 hover:text-white"
                      title="Copy to clipboard"
                    >
                      <Clipboard className="h-4 w-4" />
                    </button>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/10 flex flex-wrap gap-2">
                      {msg.sources.map((s: any, j: number) => (
                        <span key={j} className="text-[10px] bg-white/5 px-2 py-1 rounded-lg text-slate-400 border border-white/5">
                          Source: {s.title || "Document"}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/5 border border-white/10 rounded-3xl rounded-tl-none p-6 flex gap-2">
                <div className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce" />
                <div className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:200ms]" />
                <div className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:400ms]" />
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-8 pt-0">
          <form onSubmit={onSubmit} className="relative group">
            <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-indigo-500 to-cyan-500 opacity-20 blur transition duration-1000 group-hover:opacity-30"></div>
            <div className="relative flex items-center bg-slate-950/80 rounded-2xl border border-white/10 p-2 shadow-2xl backdrop-blur-xl">
              <input 
                type="text" 
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Type your question..."
                className="flex-1 bg-transparent border-none px-6 py-3 text-sm text-white focus:outline-none"
              />
              <button 
                type="submit"
                disabled={!question.trim() || isLoading}
                className="h-10 w-10 rounded-xl bg-indigo-500 flex items-center justify-center text-white transition hover:scale-105 hover:brightness-110 disabled:opacity-50"
              >
                <ArrowUp className="h-5 w-5" />
              </button>
            </div>
          </form>
          {error && <p className="mt-2 text-[10px] text-red-400 text-center uppercase font-bold tracking-widest">{error}</p>}
        </div>

        {/* Settings Modal (Restored Complexity) */}
        {isSettingsOpen && (
          <div className="absolute inset-0 z-20 bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-8 animate-in fade-in duration-300">
            <div className="w-full max-w-2xl bg-slate-900 rounded-[2.5rem] border border-white/10 overflow-hidden shadow-2xl">
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-white/5 bg-white/5">
                <h3 className="text-xl font-bold text-white">Chat Preferences</h3>
                <button onClick={() => setIsSettingsOpen(false)} className="text-slate-400 hover:text-white">
                  <X className="h-6 w-6" />
                </button>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-white/5 px-6">
                <button 
                  onClick={() => setActiveTab("general")}
                  className={`px-4 py-3 text-sm font-bold transition border-b-2 ${activeTab === 'general' ? 'border-indigo-500 text-white' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
                >
                  General
                </button>
                <button 
                  onClick={() => setActiveTab("advanced")}
                  className={`px-4 py-3 text-sm font-bold transition border-b-2 ${activeTab === 'advanced' ? 'border-indigo-500 text-white' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
                >
                  Advanced
                </button>
              </div>

              <div className="p-8 space-y-6 max-h-[60vh] overflow-y-auto">
                {activeTab === "general" ? (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                        <Search className="h-3 w-3" /> Document Focus
                      </label>
                      <select 
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        className="w-full rounded-xl bg-white/5 border border-white/10 p-3 text-sm text-white focus:outline-none focus:border-indigo-500/50"
                      >
                        <option value="All">All Documents</option>
                        <option value="Financial">Financial</option>
                        <option value="F&B">F&B</option>
                        <option value="Ticketing">Ticketing</option>
                        <option value="Retail">Retail</option>
                        <option value="Player Sales">Player Sales</option>
                        <option value="Sponsors">Sponsors</option>
                        <option value="Legal">Legal</option>
                        <option value="HR">HR</option>
                        <option value="Operations">Operations</option>
                        <option value="Others">Others</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                        <Coins className="h-3 w-3" /> Target Currency
                      </label>
                      <select 
                        value={targetCurrency}
                        onChange={(e) => setTargetCurrency(e.target.value)}
                        className="w-full rounded-xl bg-white/5 border border-white/10 p-3 text-sm text-white focus:outline-none focus:border-indigo-500/50"
                      >
                        {CURRENCY_OPTIONS.map(c => (
                          <option key={c.code} value={c.code}>{c.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10">
                      <div className="flex items-center gap-3">
                        <Globe className="h-5 w-5 text-indigo-400" />
                        <div>
                          <p className="text-sm font-medium text-white">Translate to English</p>
                          <p className="text-[10px] text-slate-500">Enable for non-English sources</p>
                        </div>
                      </div>
                      <input 
                        type="checkbox" 
                        checked={translateToEnglish}
                        onChange={(e) => setTranslateToEnglish(e.target.checked)}
                        className="h-5 w-5 rounded border-white/10 bg-indigo-500/20 text-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                          <Cpu className="h-3 w-3" /> Provider
                        </label>
                        <select 
                          value={provider}
                          onChange={(e) => setProvider(e.target.value)}
                          className="w-full rounded-xl bg-white/5 border border-white/10 p-3 text-sm text-white focus:outline-none"
                        >
                          <option value="openai">OpenAI</option>
                          <option value="bedrock">AWS Bedrock</option>
                        </select>
                      </div>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                          <Settings2 className="h-3 w-3" /> AI Model
                        </label>
                        <select 
                          value={model}
                          onChange={(e) => setModel(e.target.value)}
                          className="w-full rounded-xl bg-white/5 border border-white/10 p-3 text-sm text-white focus:outline-none"
                        >
                          <option value="auto">Auto-Select</option>
                          {availableModels.map(m => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                        <FileIcon className="h-3 w-3" /> Prompt Template
                      </label>
                      <select 
                        value={selectedPrompt}
                        onChange={(e) => setSelectedPrompt(e.target.value)}
                        className="w-full rounded-xl bg-white/5 border border-white/10 p-3 text-sm text-white focus:outline-none"
                      >
                        <option value="">No Template (Default)</option>
                        {prompts.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="pt-4 border-t border-white/5">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4">Quick Upload</p>
                      <div className="relative group cursor-pointer">
                        <input 
                          type="file" 
                          multiple 
                          onChange={onFileUpload}
                          className="absolute inset-0 z-10 w-full h-full opacity-0 cursor-pointer"
                        />
                        <div className="flex flex-col items-center justify-center p-8 rounded-3xl border-2 border-dashed border-white/10 bg-white/2 transition group-hover:bg-indigo-500/5 group-hover:border-indigo-500/30">
                          {isUploading ? <Loader2 className="h-8 w-8 animate-spin text-indigo-400" /> : <UploadCloud className="h-8 w-8 text-slate-600" />}
                          <p className="mt-2 text-xs text-slate-400">Upload documents directly to chat context</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-6 bg-white/5 flex justify-end">
                <button 
                  onClick={() => setIsSettingsOpen(false)}
                  className="rounded-2xl bg-indigo-500 px-8 py-3 text-sm font-bold text-white transition hover:brightness-110 active:scale-95"
                >
                  Save & Apply
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
