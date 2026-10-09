// Adapted from Bilun cafa27bc; Copyright (c) 2026 Safa Öksüz. All rights reserved.
/**
 * Chip — single status/badge primitive.
 *
 * Replaces `.sut-status-chip`, `.badge-aaa`/`.badge-aa`/`.badge-a`/etc.,
 * and ad-hoc inline-styled `<span>` chips throughout the app.
 *
 * Variants map to status tokens (separate from brand). The `gold`
 * variant is reserved for emphasis on actionable items and should
 * never indicate status.
 */

import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export type ChipVariant =
  | "neutral"
  | "success"
  | "warning"
  | "danger"
  | "gold"
  | "outline";

export interface ChipProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: ChipVariant;
  leading?: ReactNode;
  trailing?: ReactNode;
  children?: ReactNode;
}

const VARIANT_CLASS: Record<ChipVariant, string> = {
  neutral:
    "bg-[var(--surface-soft)] text-[var(--text-secondary)] border border-transparent",
  success:
    "bg-[color-mix(in_srgb,var(--success)_10%,transparent)] text-[var(--success)] border border-[color-mix(in_srgb,var(--success)_22%,transparent)]",
  warning:
    "bg-[color-mix(in_srgb,var(--warning)_10%,transparent)] text-[var(--warning)] border border-[color-mix(in_srgb,var(--warning)_22%,transparent)]",
  danger:
    "bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] text-[var(--danger)] border border-[color-mix(in_srgb,var(--danger)_22%,transparent)]",
  gold:
    "bg-[var(--gold-subtle)] text-[var(--gold-pressed)] border border-[color-mix(in_srgb,var(--gold)_30%,transparent)]",
  outline:
    "bg-transparent text-[var(--text-secondary)] border border-[var(--border-strong)]",
};

export default function Chip({
  variant = "neutral",
  leading,
  trailing,
  className,
  children,
  ...rest
}: ChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.7rem] font-semibold leading-5 tracking-[0.04em]",
        VARIANT_CLASS[variant],
        className,
      )}
      {...rest}
    >
      {leading ? <span className="inline-flex">{leading}</span> : null}
      <span>{children}</span>
      {trailing ? <span className="inline-flex">{trailing}</span> : null}
    </span>
  );
}
