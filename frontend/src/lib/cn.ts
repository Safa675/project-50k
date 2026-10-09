// Adapted from Bilun cafa27bc; Copyright (c) 2026 Safa Öksüz. All rights reserved.
/**
 * Class-name composer for the BILUN design system primitives.
 *
 * `clsx` handles conditional truthiness; `tailwind-merge` resolves
 * conflicting Tailwind utility classes so a caller-supplied
 * `className` can always override primitive defaults.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
