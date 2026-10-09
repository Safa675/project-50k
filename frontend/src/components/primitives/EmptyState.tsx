// Adapted from Bilun cafa27bc; Copyright (c) 2026 Safa Öksüz. All rights reserved.
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface EmptyStateProps {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/**
 * Quiet empty state — no dashed "under construction" borders.
 */
export default function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex min-h-[12rem] flex-col items-center justify-center gap-3 rounded-[var(--r-lg)]",
        "border border-[var(--border-subtle)] bg-[var(--surface-base)] px-6 py-10 text-center",
        className,
      )}
    >
      {icon ? (
        <div className="text-[var(--text-muted)]" aria-hidden="true">
          {icon}
        </div>
      ) : null}
      <p className="text-sm font-medium text-[var(--text-primary)]">{title}</p>
      {description ? (
        <p className="max-w-md text-sm leading-relaxed text-[var(--text-secondary)]">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
