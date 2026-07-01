"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Send, Sparkles } from "lucide-react";
import { CitationList } from "@/components/CitationList";
import { Markdown } from "@/components/Markdown";
import { api, streamQuery } from "@/lib/api";
import type { Citation, Document } from "@/lib/types";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  streaming?: boolean;
}

function ChatInner() {
  const searchParams = useSearchParams();
  const [docs, setDocs] = useState<Document[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listDocuments().then((r) => {
      const ready = r.items.filter((d) => d.status === "ready");
      setDocs(ready);
      const preselect = searchParams.get("doc");
      if (preselect) setSelected(new Set([preselect]));
    });
  }, [searchParams]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  function toggleDoc(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function send() {
    const query = input.trim();
    if (!query || busy) return;
    setInput("");
    setBusy(true);

    setMessages((m) => [
      ...m,
      { role: "user", content: query, citations: [] },
      { role: "assistant", content: "", citations: [], streaming: true },
    ]);

    const updateAssistant = (fn: (msg: ChatMsg) => ChatMsg) =>
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = fn(copy[copy.length - 1]);
        return copy;
      });

    await streamQuery(
      {
        query,
        document_ids: selected.size ? Array.from(selected) : null,
        conversation_id: conversationId,
      },
      {
        onMeta: (cid) => setConversationId(cid),
        onCitations: (cits) => updateAssistant((msg) => ({ ...msg, citations: cits })),
        onToken: (text) =>
          updateAssistant((msg) => ({ ...msg, content: msg.content + text })),
        onDone: (answer) =>
          updateAssistant((msg) => ({
            ...msg,
            content: answer || msg.content,
            streaming: false,
          })),
        onError: (err) =>
          updateAssistant((msg) => ({
            ...msg,
            content: `⚠️ ${err}`,
            streaming: false,
          })),
      }
    );
    setBusy(false);
  }

  return (
    <div className="flex h-screen flex-col">
      {/* Document scope selector */}
      <div className="border-b border-slate-200 p-4 dark:border-ink-700">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Scope:</span>
          <button
            onClick={() => setSelected(new Set())}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              selected.size === 0
                ? "bg-brand-500 text-white"
                : "border border-slate-300 dark:border-ink-600"
            }`}
          >
            All papers
          </button>
          {docs.map((d) => (
            <button
              key={d.id}
              onClick={() => toggleDoc(d.id)}
              className={`max-w-[200px] truncate rounded-full px-3 py-1 text-xs font-medium transition ${
                selected.has(d.id)
                  ? "bg-brand-500 text-white"
                  : "border border-slate-300 dark:border-ink-600"
              }`}
              title={d.title}
            >
              {d.title}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 p-6">
          {messages.length === 0 && (
            <div className="mt-20 text-center">
              <Sparkles className="mx-auto mb-3 text-brand-500" size={32} />
              <h2 className="text-xl font-semibold">Ask your papers anything</h2>
              <p className="mt-2 text-sm text-slate-500">
                Try “Explain the methodology” or “What datasets were used?”
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className="animate-fade-in">
              {m.role === "user" ? (
                <div className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2 text-sm text-white">
                    {m.content}
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl rounded-bl-sm bg-white p-4 shadow-sm dark:bg-ink-800">
                  {m.content ? (
                    <Markdown>{m.content}</Markdown>
                  ) : (
                    <span className="text-sm text-slate-400">Thinking…</span>
                  )}
                  {m.streaming && m.content && (
                    <span className="ml-0.5 inline-block h-4 w-1.5 animate-blink bg-brand-500 align-middle" />
                  )}
                  <CitationList citations={m.citations} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Composer */}
      <div className="border-t border-slate-200 p-4 dark:border-ink-700">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            placeholder="Ask a question about your papers…"
            className="input max-h-40 flex-1 resize-none"
          />
          <button onClick={send} disabled={busy || !input.trim()} className="btn-primary h-[42px]">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-slate-500">Loading chat…</div>}>
      <ChatInner />
    </Suspense>
  );
}
