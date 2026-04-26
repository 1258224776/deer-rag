import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

type SubpageHeaderProps = {
  label: string;
  title: string;
  description?: string;
  backLabel: string;
  backHref?: string;
  children?: ReactNode;
};

export function SubpageHeader({
  label,
  title,
  description,
  backLabel,
  backHref = "/collections",
  children,
}: SubpageHeaderProps) {
  return (
    <section className="panel-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <span className="section-label">{label}</span>
          <h1 className="mt-3 font-[Bahnschrift,Aptos,sans-serif] text-4xl font-semibold tracking-tight text-[color:var(--ink)]">
            {title}
          </h1>
          {description ? (
            <p className="mt-3 max-w-3xl text-sm leading-7 text-[color:var(--muted)]">
              {description}
            </p>
          ) : null}
        </div>

        <Link href={backHref} className="button-secondary shrink-0">
          <ArrowLeft className="size-4" />
          {backLabel}
        </Link>
      </div>

      {children ? <div className="mt-6">{children}</div> : null}
    </section>
  );
}
