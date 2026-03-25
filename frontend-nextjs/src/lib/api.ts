import { API_PROXY_BASE_URL, BACKEND_API_BASE_URL } from "@/lib/config";

export type AuthResponse = {
  access_token: string;
  token_type: string;
};

export type HealthResponse = {
  status: string;
  app: string;
};

export type DocumentItem = {
  id: string;
  title: string;
  category: string;
  uploaded_by: string;
  timestamp: string | null;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: string;
};

export type PromptItem = {
  id: string;
  name: string;
  category: string | null;
  template: string;
  description: string | null;
  created_at: string | null;
};

export type ConversationItem = {
  session_id: string;
  title: string | null;
  category: string | null;
  message_count: number;
  timestamp: string | null;
  updated_at: string | null;
};

export type QueryResponse = {
  answer: string;
  sources: Array<{ title?: string; doc_id?: string; excerpt?: string }>;
  model_used: string;
  session_id: string;
};

export type ReportResponse = {
  report: string;
  generated_at?: string;
  model_used?: string;
  report_type?: string;
  output_format?: string;
};

export type UploadBatchResponse = {
  batch_id: string;
  total_submitted: number;
  accepted: number;
  rejected: number;
  duplicates: number;
  files: Array<{
    filename: string;
    status: "processing" | "rejected" | "duplicate";
    reason?: string;
    document_id?: string;
    existing_id?: string;
  }>;
};

export type BatchStatusResponse = {
  batch_id: string;
  total: number;
  ready: number;
  processing: number;
  failed: number;
  files: Record<
    string,
    {
      filename: string;
      status: "ready" | "processing" | "failed";
      chunks?: number;
      error?: string;
      is_duplicate?: boolean;
    }
  >;
};

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_PROXY_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch (error) {
    throw new Error(
      error instanceof Error
        ? `Network request failed: ${error.message}`
        : "Network request failed."
    );
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // ignore JSON parsing failure and keep generic message
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function register(username: string, password: string) {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function login(username: string, password: string) {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getHealth(token?: string) {
  return request<HealthResponse>("/health", { method: "GET" }, token);
}

export function getModels(token?: string) {
  return request<{ models: string[] }>("/models", { method: "GET" }, token);
}

export function listDocuments(token?: string, limit = 200) {
  return request<{ total: number; documents: DocumentItem[] }>(
    `/documents?limit=${limit}`,
    { method: "GET" },
    token
  );
}

export function deleteDocument(documentId: string, token?: string) {
  return request<{ deleted: boolean; document_id: string }>(
    `/documents/${documentId}`,
    { method: "DELETE" },
    token
  );
}

export function uploadBatch(files: File[], category: string, token?: string) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  form.append("category", category || "general");

  return fetch(`${BACKEND_API_BASE_URL}/upload_batch`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  }).then(async (response) => {
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) {
          message = body.detail;
        }
      } catch {
        // keep generic message if response is not JSON
      }
      throw new Error(message);
    }
    return (await response.json()) as UploadBatchResponse;
  });
}

export function getBatchStatus(batchId: string, token?: string) {
  return request<BatchStatusResponse>(`/batch_status/${batchId}`, { method: "GET" }, token);
}

export function listPrompts(token?: string) {
  return request<{ prompts: PromptItem[] }>("/prompts", { method: "GET" }, token);
}

export function createPrompt(
  payload: { name: string; template: string; category?: string; description?: string },
  token?: string
) {
  return request<{ id: string; name: string; message: string }>(
    "/prompts",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

export function deletePrompt(promptId: string, token?: string) {
  return request<{ deleted: boolean; prompt_id: string }>(
    `/prompts/${promptId}`,
    { method: "DELETE" },
    token
  );
}

export function listConversations(token?: string, category?: string) {
  const query = category ? `?limit=50&category=${encodeURIComponent(category)}` : "?limit=50";
  return request<{ conversations: ConversationItem[] }>(
    `/conversations${query}`,
    { method: "GET" },
    token
  );
}

export function listConversationCategories(token?: string) {
  return request<{ categories: string[] }>("/conversations/categories", { method: "GET" }, token);
}

export function getConversation(sessionId: string, token?: string) {
  return request<{
    session_id: string;
    title: string | null;
    category: string | null;
    messages: Array<{
      role: "user" | "assistant";
      content: string;
      sources?: Array<{ title?: string; excerpt?: string }>;
      timestamp?: string;
    }>;
    timestamp: string | null;
  }>(`/conversations/${sessionId}`, { method: "GET" }, token);
}

export function queryDocuments(
  payload: {
    question: string;
    model?: string;
    top_k?: number;
    temperature?: number;
    category?: string | null;
    session_id?: string;
    prompt_template?: string;
    openai_api_key?: string | null;
    anthropic_api_key?: string | null;
    gemini_api_key?: string | null;
  },
  token?: string
) {
  return request<QueryResponse>(
    "/query",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

export function getAnalyticsOverview(token?: string) {
  return request<{
    total_documents: number;
    total_chunks: number;
    total_size_mb?: number;
    by_category: Record<string, number>;
    by_file_type: Record<string, number>;
    by_status: Record<string, number>;
    by_uploader?: Record<string, number>;
  }>("/analytics/overview", { method: "GET" }, token);
}

export function getAnalyticsContent(token?: string) {
  return request<{
    total_estimated_words: number;
    total_reading_time_min: number;
    word_frequencies: Record<string, number>;
  }>("/analytics/content", { method: "GET" }, token);
}

export function getAnalyticsStorage(token?: string) {
  return request<{
    size_by_type: Record<string, number>;
    size_distribution: Record<string, number>;
  }>("/analytics/storage", { method: "GET" }, token);
}

export function getAnalyticsContentInsights(token?: string) {
  return request<{
    topics: Array<{ topic: string; frequency: number; type?: string }>;
    entities?: {
      monetary?: Array<{ value: string; occurrences: number }>;
      percentages?: Array<{ value: string; occurrences: number }>;
      dates?: Array<{ value: string; occurrences: number }>;
      emails?: Array<{ value: string; occurrences: number }>;
      urls?: Array<{ value: string; occurrences: number }>;
      organizations?: Array<{ value: string; occurrences: number }>;
    };
    financials?: Array<{
      keyword: string;
      context: string;
      values_found?: string[];
    }>;
    summary: {
      total_topics: number;
      total_entities: number;
      total_financial_items: number;
      docs_analyzed: number;
      chunks_analyzed: number;
    };
  }>("/analytics/content_insights", { method: "GET" }, token);
}

export function generateReport(
  payload: {
    topic: string;
    query: string;
    report_type?: string;
    output_format?: "markdown" | "table" | "json";
    model?: string;
    top_k?: number;
    openai_api_key?: string | null;
    anthropic_api_key?: string | null;
    gemini_api_key?: string | null;
  },
  token?: string
) {
  return request<ReportResponse>(
    "/generate_report",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

