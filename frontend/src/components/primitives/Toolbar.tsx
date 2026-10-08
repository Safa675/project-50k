// Adapted from Bilun cafa27bc; Copyright (c) 2026 Safa Öksüz. All rights reserved.
/**
 * Toolbar — search + filter + paginate row primitive.
 *
 * Replaces bespoke `<div className="flex flex-wrap items-end gap-...">`
 * compositions in `SUTOptimizerTab` (`AlertQueryBar`) and explorer
 * filter bars. The primitive itself is layout-only; callers compose
 * filter controls from `<input>`, `<select>`, or Radix Select.
 *
 * Slots:
 * - `leading`   — left-aligned content (search input, etc.)
 * - `children`  — central flex area for filters
 * - `trailing`  — right-aligned content (paginate, reset, etc.)
 */

import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface ToolbarProps extends HTMLAttributes<HTMLDivElement> {
  leading?: ReactNode;
  trailing?: ReactNode;
  children?: ReactNode;
}

export default function Toolbar({
  leading,
  trailing,
  className,
  children,
  ...rest
}: ToolbarProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-end justify-between gap-3 rounded-[var(--r-lg)] border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3",
        className,
      )}
      {...rest}
    >
      {leading ? <div className="flex items-center gap-3">{leading}</div> : null}
      {children ? (
        <div className="flex flex-wrap items-end gap-3">{children}</div>
      ) : null}
      {trailing ? <div className="flex items-center gap-2">{trailing}</div> : null}
    </div>
  );
}
