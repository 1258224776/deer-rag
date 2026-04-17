"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import * as Separator from "@radix-ui/react-separator";
import { Beaker, DatabaseZap, FolderKanban, Languages, Search, Sparkles } from "lucide-react";

import { apiBaseUrl } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const { locale, setLocale, t } = useI18n();
  const navItems = [
    {
      href: "/collections",
      label: t.sidebar.nav.collectionsLabel,
      description: t.sidebar.nav.collectionsDescription,
      icon: FolderKanban,
    },
    {
      href: "/ingest",
      label: t.sidebar.nav.ingestLabel,
      description: t.sidebar.nav.ingestDescription,
      icon: DatabaseZap,
    },
    {
      href: "/search",
      label: t.sidebar.nav.searchLabel,
      description: t.sidebar.nav.searchDescription,
      icon: Search,
    },
    {
      href: "/experiments",
      label: t.sidebar.nav.experimentsLabel,
      description: t.sidebar.nav.experimentsDescription,
      icon: Beaker,
    },
  ];

  return (
    <aside className="surface-card sticky top-4 z-20 w-full shrink-0 overflow-hidden px-4 py-4 lg:w-[290px] lg:px-5 lg:py-6">
      <div className="space-y-6">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="eyebrow-chip">{t.sidebar.badge}</span>
            <div className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] bg-white/70 p-1">
              <span className="sr-only">{t.sidebar.language}</span>
              <button
                type="button"
                onClick={() => setLocale("en")}
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-semibold transition",
                  locale === "en" ? "bg-[color:var(--ink)] text-white" : "text-[color:var(--muted)] hover:bg-black/5",
                )}
              >
                {t.sidebar.english}
              </button>
              <button
                type="button"
                onClick={() => setLocale("zh")}
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-semibold transition",
                  locale === "zh" ? "bg-[color:var(--ink)] text-white" : "text-[color:var(--muted)] hover:bg-black/5",
                )}
              >
                {t.sidebar.chinese}
              </button>
            </div>
          </div>
          <div className="space-y-2">
            <p className="font-[Bahnschrift,Aptos,sans-serif] text-3xl font-semibold tracking-tight text-[color:var(--ink)]">
              deer-rag
            </p>
            <p className="hidden max-w-[22ch] text-sm leading-6 text-[color:var(--muted)] lg:block">
              {t.sidebar.description}
            </p>
          </div>
        </div>

        <Separator.Root className="h-px bg-[color:var(--border)]" decorative />

        <nav className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
          {navItems.map((item) => {
            const active = pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-start gap-3 rounded-[22px] border px-4 py-3 transition duration-200",
                  active
                    ? "border-transparent bg-[color:var(--ink)] text-white shadow-[0_18px_30px_rgba(19,38,31,0.18)]"
                    : "border-transparent text-[color:var(--ink)] hover:border-[color:var(--border)] hover:bg-white/70",
                )}
              >
                <span
                  className={cn(
                    "mt-1 inline-flex size-10 shrink-0 items-center justify-center rounded-2xl transition duration-200",
                    active ? "bg-white/12 text-white" : "bg-[color:var(--accent-soft)] text-[color:var(--accent)]",
                  )}
                >
                  <Icon className="size-5" />
                </span>
                <span className="space-y-1">
                  <span className="block text-sm font-semibold">{item.label}</span>
                  <span
                    className={cn(
                      "hidden text-sm leading-5 lg:block",
                      active ? "text-white/72" : "text-[color:var(--muted)]",
                    )}
                  >
                    {item.description}
                  </span>
                </span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mt-6 space-y-4">
        <div className="panel-card p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Sparkles className="size-4 text-[color:var(--ember)]" />
            {t.sidebar.apiTarget}
          </div>
          <p className="break-all rounded-2xl bg-[color:var(--background-strong)] px-3 py-2 text-xs font-medium text-[color:var(--muted)]">
            {apiBaseUrl}
          </p>
        </div>
        <div className="hidden rounded-[22px] bg-[color:var(--accent-soft)] p-4 lg:block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--accent)]">
            <Languages className="size-4" />
            {t.sidebar.language}
          </div>
          <p className="text-xs leading-5 text-[color:var(--muted)]">{t.sidebar.footer}</p>
        </div>
      </div>
    </aside>
  );
}
