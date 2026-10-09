// Adapted from Bilun cafa27bc; Copyright (c) 2026 Safa Öksüz. All rights reserved.
/**
 * Stat — replacement for `KpiCard`, `.metric-card`, `.frost-kpi-card`.
 *
 * Left-aligned, tabular numerics, generous label/value gap. When
 * `display="gold"`, the value renders in Fraunces italic gold — the
 * deck's signature treatment, reserved for the **primary** KPI on a
 * page (max one per screen).
 */

import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export type StatDisplay = "default" | "gold";

export interface StatProps extends HTMLAttributes<HTMLDivElement> {
  label: ReactNode;
  value: ReactNode;
  delta?: ReactNode;
  /** `gold` renders the value in Fraunces italic gold (use sparingly). */
  display?: StatDisplay;
  /** Optional muted hint shown under value. */
  hint?: ReactNode;
}

export default function Stat({
  label,
  value,
  delta,
  display = "default",
  hint,
  className,
  ...rest
}: StatProps) {
  const valueClass =
    display === "gold"
      ? "font-[var(--font-display)] italic text-[var(--gold)] text-3xl leading-none tracking-tight"
      : "font-sans text-[var(--text-primary)] text-2xl leading-none font-semibold tracking-tight";

  return (
    <div className={cn("flex flex-col gap-2", className)} {...rest}>
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
        {label}
      </p>
      <div className="flex items-baseline gap-2">
        <span className={cn(valueClass, "tabular-nums lining-nums")}>{value}</span>
        {delta ? (
          <span className="text-xs font-medium text-[var(--text-secondary)] tabular-nums">
            {delta}
          </span>
        ) : null}
      </div>
      {hint ? (
        <p className="text-xs text-[var(--text-muted)] leading-snug">{hint}</p>
      ) : null}
    </div>
  );
}
