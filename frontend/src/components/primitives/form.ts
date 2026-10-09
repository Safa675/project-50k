// Adapted from Bilun cafa27bc; Copyright (c) 2026 Safa Öksüz. All rights reserved.
/**
 * Shared form-control class strings.
 *
 * Replaces the legacy `.sut-input` and `.app-select` rules from
 * `legacy.css` (Phase 5 cleanup). Use on `<input>`, `<select>`, and
 * `<textarea>` elements via `className={inputClass}` (compose extra
 * utilities with the `cn()` helper).
 *
 * Tokens: `--border-subtle`, `--surface-base`, `--text-primary`,
 * `--text-muted`, `--gold`, `--r-md`, `--dur`, `--ease`.
 *
 * The focus treatment matches `SutInlineAIPanel`'s chat input — a gold
 * border plus a 2px gold-tinted ring — so all text controls share one
 * focus affordance across the app.
 */

const FOCUS_RING =
  "focus:border-[var(--gold)] focus:outline-none focus:shadow-[0_0_0_2px_color-mix(in_srgb,var(--gold)_15%,transparent)]";

/**
 * Base text control (input / textarea). 1:1 with the old `.sut-input`:
 * full width, 8px×12px padding, `--r-md` radius, subtle border over the
 * base surface, 0.875rem primary text, muted placeholder.
 */
export const inputClass = [
  "w-full rounded-[var(--r-md)] border border-[var(--border-subtle)] bg-[var(--surface-base)]",
  "px-3 py-2 text-[0.875rem] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]",
  "outline-none transition-[border-color] duration-[var(--dur)] ease-[var(--ease)]",
  FOCUS_RING,
].join(" ");

/**
 * `<select>` control. Extends `inputClass` with a clickable cursor and a
 * wider min width so short option lists don't collapse. Keeps the
 * browser-native dropdown arrow (the old `.app-select` hid it behind a
 * CSS-gradient chevron; we keep the native affordance for reliability).
 */
export const selectClass = [inputClass, "min-w-[140px] cursor-pointer pr-8"].join(" ");
