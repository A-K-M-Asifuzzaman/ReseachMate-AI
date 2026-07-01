"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  GitGraph,
  History,
  LayoutDashboard,
  Library,
  LogOut,
  MessagesSquare,
  Sparkles,
  Upload,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ThemeToggle } from "./ThemeToggle";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/chat", label: "AI Chat", icon: MessagesSquare },
  { href: "/library", label: "Library", icon: Library },
  { href: "/graph", label: "Knowledge Graph", icon: GitGraph },
  { href: "/history", label: "History", icon: History },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-4 dark:border-ink-700 dark:bg-ink-800">
      <Link href="/dashboard" className="mb-6 flex items-center gap-2 px-2 text-lg font-semibold">
        <Sparkles className="text-brand-500" size={22} />
        ResearchMate
      </Link>

      <nav className="flex-1 space-y-1">
        {nav.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                active
                  ? "bg-brand-500/10 text-brand-500"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-ink-700"
              }`}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-4 space-y-3 border-t border-slate-200 pt-4 dark:border-ink-700">
        <div className="flex items-center justify-between px-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{user?.name}</p>
            <p className="truncate text-xs text-slate-500">{user?.email}</p>
          </div>
          <ThemeToggle />
        </div>
        <button onClick={logout} className="btn-ghost w-full justify-start">
          <LogOut size={16} /> Log out
        </button>
      </div>
    </aside>
  );
}
