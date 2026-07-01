import Link from "next/link";
import {
  BookOpen,
  GitGraph,
  MessagesSquare,
  Quote,
  Search,
  Sparkles,
} from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";

const features = [
  {
    icon: Search,
    title: "Hybrid RAG",
    body: "Dense + BM25 retrieval, RRF fusion, and cross-encoder reranking for precise answers.",
  },
  {
    icon: Quote,
    title: "Grounded citations",
    body: "Every claim is backed by the exact paper, page, and section it came from.",
  },
  {
    icon: BookOpen,
    title: "Summaries",
    body: "Short abstracts or structured breakdowns: problem, method, dataset, results, limits.",
  },
  {
    icon: MessagesSquare,
    title: "Chat with memory",
    body: "Follow-up questions across your library, with streaming answers.",
  },
  {
    icon: GitGraph,
    title: "Knowledge graph",
    body: "Extract entities and relations into an explorable graph of concepts.",
  },
  {
    icon: Sparkles,
    title: "Agents",
    body: "Research, summary, citation, and comparison agents planned automatically.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="text-brand-500" size={22} />
          ResearchMate <span className="text-brand-500">AI</span>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link href="/login" className="btn-ghost">
            Log in
          </Link>
          <Link href="/register" className="btn-primary">
            Get started
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-6 pb-16 pt-20 text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand-500/30 bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-400">
          <Sparkles size={14} /> Retrieval-Augmented research assistant
        </div>
        <h1 className="text-balance text-5xl font-bold tracking-tight sm:text-6xl">
          Understand any paper,
          <span className="bg-gradient-to-r from-brand-400 to-fuchsia-400 bg-clip-text text-transparent">
            {" "}
            with citations.
          </span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-500 dark:text-slate-400">
          Upload research PDFs and ask questions in plain language. ResearchMate reads,
          retrieves, and reasons — then answers with sources you can verify.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link href="/register" className="btn-primary px-6 py-3 text-base">
            Start for free
          </Link>
          <Link href="/login" className="btn-ghost px-6 py-3 text-base">
            I have an account
          </Link>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-5 px-6 pb-24 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="card animate-fade-in">
            <f.icon className="mb-3 text-brand-500" size={24} />
            <h3 className="mb-1 font-semibold">{f.title}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-500 dark:border-ink-700">
        Built with FastAPI · Qdrant · Neo4j · Next.js
      </footer>
    </div>
  );
}
