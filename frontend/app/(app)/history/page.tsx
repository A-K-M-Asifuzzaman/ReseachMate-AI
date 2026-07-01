"use client";

import { useEffect, useState } from "react";
import { MessagesSquare, Trash2 } from "lucide-react";
import { CitationList } from "@/components/CitationList";
import { Markdown } from "@/components/Markdown";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { Conversation, ConversationDetail } from "@/lib/types";

export default function HistoryPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const r = await api.listConversations();
    setConversations(r.items);
    setLoading(false);
  }
  useEffect(() => {
    refresh();
  }, []);

  async function open(id: string) {
    setActive(await api.getConversation(id));
  }

  async function remove(id: string) {
    if (!confirm("Delete this conversation?")) return;
    await api.deleteConversation(id);
    if (active?.id === id) setActive(null);
    refresh();
  }

  return (
    <div className="mx-auto flex max-w-6xl gap-6 p-8">
      <div className="w-72 shrink-0">
        <PageHeader title="History" />
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : conversations.length === 0 ? (
          <p className="text-sm text-slate-500">No conversations yet.</p>
        ) : (
          <div className="space-y-2">
            {conversations.map((c) => (
              <div
                key={c.id}
                className={`group flex items-center justify-between rounded-lg border p-3 text-sm transition ${
                  active?.id === c.id
                    ? "border-brand-500 bg-brand-500/5"
                    : "border-slate-200 hover:border-brand-500 dark:border-ink-700"
                }`}
              >
                <button onClick={() => open(c.id)} className="flex min-w-0 items-center gap-2 text-left">
                  <MessagesSquare size={15} className="shrink-0 text-slate-400" />
                  <span className="truncate">{c.title}</span>
                </button>
                <button
                  onClick={() => remove(c.id)}
                  className="opacity-0 transition group-hover:opacity-100"
                >
                  <Trash2 size={14} className="text-red-500" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1">
        {active ? (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold">{active.title}</h2>
            {active.messages.map((m) => (
              <div key={m.id}>
                {m.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2 text-sm text-white">
                      {m.content}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl rounded-bl-sm bg-white p-4 shadow-sm dark:bg-ink-800">
                    <Markdown>{m.content}</Markdown>
                    <CitationList citations={m.citations} />
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="flex h-96 items-center justify-center text-sm text-slate-500">
            Select a conversation to view it.
          </div>
        )}
      </div>
    </div>
  );
}
