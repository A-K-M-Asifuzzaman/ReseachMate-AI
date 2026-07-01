export interface User {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface TokenWithUser {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export interface Document {
  id: string;
  title: string;
  authors?: string | null;
  year?: number | null;
  journal?: string | null;
  abstract?: string | null;
  filename: string;
  file_size?: number | null;
  num_pages?: number | null;
  num_chunks: number;
  status: DocumentStatus;
  error?: string | null;
  created_at: string;
}

export interface Citation {
  document_id: string;
  chunk_id: string;
  title: string;
  authors?: string | null;
  page_number?: number | null;
  section?: string | null;
  snippet: string;
  score: number;
}

export interface RAGAnswer {
  answer: string;
  citations: Citation[];
  conversation_id?: string | null;
  query: string;
  expanded_queries: string[];
  latency_ms?: number | null;
  tokens_used?: number | null;
}

export interface Conversation {
  id: string;
  title: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface DetailedSummary {
  problem: string;
  methodology: string;
  dataset: string;
  model: string;
  results: string;
  limitations: string;
}

export interface SummaryResponse {
  document_id: string;
  summary_type: "short" | "detailed";
  short_summary?: string | null;
  detailed_summary?: DetailedSummary | null;
  tokens_used: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  weight: number;
}
export interface GraphEdge {
  source: string;
  target: string;
  label: string;
}
export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ComparisonRow {
  dimension: string;
  cells: Record<string, string>;
}
export interface ComparisonResponse {
  papers: { document_id: string; title: string }[];
  rows: ComparisonRow[];
  synthesis: string;
  tokens_used: number;
}
