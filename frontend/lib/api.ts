import type {
  ComparisonResponse,
  Conversation,
  ConversationDetail,
  Document,
  GraphResponse,
  RAGAnswer,
  SummaryResponse,
  TokenWithUser,
  User,
} from "./types";

const BASE = "/api/v1";

const ACCESS = "rm_access";
const REFRESH = "rm_refresh";

export const tokenStore = {
  get access() {
    return typeof window === "undefined" ? null : localStorage.getItem(ACCESS);
  },
  get refresh() {
    return typeof window === "undefined" ? null : localStorage.getItem(REFRESH);
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  tokenStore.set(data.access_token, data.refresh_token);
  return true;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401 && retry && (await refreshAccessToken())) {
    return request<T>(path, options, false);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // ── auth ──────────────────────────────────────────────
  async register(name: string, email: string, password: string) {
    return request<TokenWithUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
  },
  async login(email: string, password: string) {
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({}))).detail ?? "Login failed";
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as TokenWithUser;
  },
  me() {
    return request<User>("/auth/me");
  },

  // ── documents ─────────────────────────────────────────
  async upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<Document>("/documents/upload", { method: "POST", body: form });
  },
  listDocuments() {
    return request<{ items: Document[]; total: number }>("/documents");
  },
  getDocument(id: string) {
    return request<Document>(`/documents/${id}`);
  },
  deleteDocument(id: string) {
    return request<void>(`/documents/${id}`, { method: "DELETE" });
  },
  summarize(id: string, type: "short" | "detailed") {
    return request<SummaryResponse>(`/documents/${id}/summary`, {
      method: "POST",
      body: JSON.stringify({ summary_type: type }),
    });
  },

  // ── rag / chat ────────────────────────────────────────
  query(payload: {
    query: string;
    document_ids?: string[] | null;
    conversation_id?: string | null;
  }) {
    return request<RAGAnswer>("/rag/query", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listConversations() {
    return request<{ items: Conversation[]; total: number }>("/chat/conversations");
  },
  getConversation(id: string) {
    return request<ConversationDetail>(`/chat/conversations/${id}`);
  },
  deleteConversation(id: string) {
    return request<void>(`/chat/conversations/${id}`, { method: "DELETE" });
  },

  // ── knowledge graph ───────────────────────────────────
  extractGraph(id: string) {
    return request(`/knowledge-graph/documents/${id}/extract`, { method: "POST" });
  },
  userGraph() {
    return request<GraphResponse>("/knowledge-graph");
  },
  documentGraph(id: string) {
    return request<GraphResponse>(`/knowledge-graph/documents/${id}`);
  },

  // ── comparison ────────────────────────────────────────
  compare(document_ids: string[]) {
    return request<ComparisonResponse>("/comparison", {
      method: "POST",
      body: JSON.stringify({ document_ids }),
    });
  },
};

/**
 * Stream a RAG answer over SSE. Calls the provided handlers as events arrive.
 */
export async function streamQuery(
  payload: { query: string; document_ids?: string[] | null; conversation_id?: string | null },
  handlers: {
    onMeta?: (conversationId: string) => void;
    onCitations?: (citations: any[]) => void;
    onToken?: (text: string) => void;
    onDone?: (answer: string) => void;
    onError?: (err: string) => void;
  }
): Promise<void> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const res = await fetch(`${BASE}/rag/query/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) {
    handlers.onError?.(`Request failed (${res.status})`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // Normalize CRLF (sse-starlette) to LF so frame/line splitting is consistent.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      let parsed: any;
      try {
        parsed = JSON.parse(data);
      } catch {
        continue;
      }
      if (event === "meta") handlers.onMeta?.(parsed.conversation_id);
      else if (event === "citations") handlers.onCitations?.(parsed.citations ?? []);
      else if (event === "token") handlers.onToken?.(parsed.text ?? "");
      else if (event === "done") handlers.onDone?.(parsed.answer ?? "");
    }
  }
}
