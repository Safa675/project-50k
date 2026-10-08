// Adapted from Bilun cafa27bc; Copyright (c) 2026 Safa Öksüz. All rights reserved.
/**
 * DataTable — denser, navy/gold/cream table primitive.
 *
 * Replaces `.frost-table-wrap` + `.glass-table-wrap` (which apply
 * blur, glow, gradient backgrounds, hover lift, and row-zebra — all
 * dropped from the design system per `plans/frontend-rebuild.md`).
 *
 * Behavior:
 * - Sticky header (`thead` cells use `position: sticky`)
 * - Tabular-nums applied to `.num` cells
 * - No row-zebra; subtle 1px bottom border between rows
 * - Hover row tint uses `--surface-overlay` (navy at 6%)
 *
 * Layout is composable — callers still provide `<thead>` / `<tbody>`.
 */

import type { HTMLAttributes, ThHTMLAttributes, TdHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface DataTableProps extends HTMLAttributes<HTMLDivElement> {
  /** Minimum table width before horizontal scroll kicks in. */
  minWidth?: number;
  /** Optional classes applied to the inner `<table>` element. */
  tableClassName?: string;
  children?: ReactNode;
}

export function DataTable({
  minWidth = 720,
  className,
  tableClassName,
  children,
  ...rest
}: DataTableProps) {
  return (
    <div
      className={cn(
        "overflow-x-auto rounded-[var(--r-lg)] border border-[var(--border-subtle)] bg-[var(--surface-base)]",
        className,
      )}
      {...rest}
    >
      <table
        className={cn("fund-data-table w-full border-collapse text-sm", tableClassName)}
        style={{ minWidth }}
      >
        {children}
      </table>
    </div>
  );
}

export function DataTableHeader({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn(
        "bg-[var(--surface-soft)] text-[var(--text-primary)]",
        className,
      )}
      {...rest}
    >
      {children}
    </thead>
  );
}

export function DataTableHeaderCell({
  className,
  numeric,
  children,
  ...rest
}: ThHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <th
      scope="col"
      className={cn(
        "sticky top-0 z-[1] whitespace-nowrap border-b border-[var(--border-subtle)] bg-[var(--surface-soft)] px-3 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.08em]",
        numeric ? "num-col text-right tabular-nums lining-nums" : "",
        className,
      )}
      {...rest}
    >
      {children}
    </th>
  );
}

export function DataTableBody({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody className={cn("", className)} {...rest}>
      {children}
    </tbody>
  );
}

export function DataTableRow({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "transition-[background-color] duration-[var(--dur)] ease-[var(--ease)] hover:bg-[var(--surface-overlay)]",
        className,
      )}
      {...rest}
    >
      {children}
    </tr>
  );
}

export function DataTableCell({
  className,
  numeric,
  children,
  ...rest
}: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <td
      className={cn(
        "px-3 py-2.5 align-top",
        numeric ? "num-col text-right tabular-nums lining-nums font-medium text-[var(--text-primary)]" : "",
        className,
      )}
      {...rest}
    >
      {children}
    </td>
  );
}

export default DataTable;
