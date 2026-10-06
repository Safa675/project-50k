#!/usr/bin/env python3
"""Reproducible opaque sRGB candidate-pair calculation, not a UI audit.

Formula source: https://www.w3.org/TR/WCAG22/#dfn-relative-luminance
Contrast source: https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio
Run from any directory. No network, extra package, account or font required.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def relative_luminance(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValueError("Expected an opaque six-digit sRGB hex color")
    channels = [int(value[offset:offset + 2], 16) / 255 for offset in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast_ratio(foreground, background):
    lower, upper = sorted((relative_luminance(foreground), relative_luminance(background)))
    return (upper + 0.05) / (lower + 0.05)


def arithmetic_checks():
    # Distinct invariants plus rejection of unsupported compositing input.
    assert math.isclose(contrast_ratio("#000000", "#FFFFFF"), 21.0)
    assert math.isclose(contrast_ratio("#234B5D", "#234B5D"), 1.0)
    assert math.isclose(contrast_ratio("#234B5D", "#FFFFFF"), contrast_ratio("#FFFFFF", "#234B5D"))
    assert math.isclose(relative_luminance("#000000"), 0.0)
    assert math.isclose(relative_luminance("#FFFFFF"), 1.0)
    for invalid in ("#FFF", "#FFFFFF00", "rgba(255,255,255,0.5)", "invalid", None):
        try:
            relative_luminance(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported color was accepted")
    return {"status": "PASS", "invariant_checks": 5, "unsupported_input_checks": 5}


def build_pairings(colors):
    pairs = []

    def add(label, foreground, background, category="NORMAL_TEXT", threshold=4.5, qualification=None, voluntary_target=None):
        ratio = contrast_ratio(colors[foreground], colors[background])
        pairs.append({
            "label": label, "foreground_token": foreground, "background_token": background,
            "foreground": colors[foreground], "background": colors[background],
            "category": category, "threshold": threshold, "contrast_ratio": round(ratio, 6),
            "threshold_met_using_unrounded_ratio": (ratio >= threshold if threshold is not None else None),
            "qualification": qualification, "voluntary_target": voluntary_target,
            "voluntary_target_met": (ratio >= voluntary_target if voluntary_target is not None else None)
        })

    for background in ("surface", "canvas", "soft_surface"):
        for foreground in ("text", "muted", "accent"):
            add(f"{foreground} text on {background}", foreground, background)
        add(f"external focus on {background}", "focus", background, "NON_TEXT", 3.0,
            "External outline is adjacent to this surface; actual geometry/occlusion not tested.")
        add(f"required control boundary on {background}", "control_border", background, "NON_TEXT", 3.0)
        add(f"decorative separator on {background}", "decorative_separator", background,
            "DECORATIVE_ONLY", None, "Must not be the required boundary of a control or essential chart element.")

    add("primary button label", "white", "accent")
    add("primary hover button label", "white", "accent_hover")
    add("external focus across white offset", "focus", "white", "NON_TEXT", 3.0)
    add("readable inactive control label", "disabled_text", "disabled_surface", "INACTIVE_COMPONENT", None,
        "Only genuinely inactive components are exempt; this voluntary text target is not a WCAG requirement.", 4.5)
    for severity in ("attention", "important", "critical"):
        token = f"severity_{severity}"
        add(f"{severity} event label", token, token + "_surface")
        add(f"{severity} essential icon", token, token + "_surface", "NON_TEXT", 3.0)
    for direction in ("positive", "negative"):
        token = f"price_{direction}"
        add(f"signed {direction} number on white", token, "surface")
        add(f"signed {direction} number on tint", token, token + "_surface")
    for state in ("current", "delayed", "stale", "unavailable", "replay", "synthetic"):
        token = f"data_{state}"
        add(f"{state} source/mode label", token, token + "_surface")
    for series in "abcdef":
        token = f"series_{series}"
        add(f"{token} meaningful chart stroke on white", token, "surface", "NON_TEXT", 3.0)
        add(f"{token} meaningful chart stroke on canvas", token, "canvas", "NON_TEXT", 3.0)
    return pairs


def main():
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=project_root / "research/brand_lab/color_candidates.json")
    parser.add_argument("--output", type=Path, default=project_root / "research/brand_lab/color_contrast_results.json")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    candidates = json.loads(raw)
    results = []
    for palette in candidates["palettes"]:
        colors = {**candidates["shared_semantic_colors"], **palette["colors"]}
        pairs = build_pairings(colors)
        required = [p for p in pairs if p["threshold"] is not None]
        failures = [p["label"] for p in required if not p["threshold_met_using_unrounded_ratio"]]
        text_ratios = [p["contrast_ratio"] for p in required if p["category"] == "NORMAL_TEXT"]
        nontext_ratios = [p["contrast_ratio"] for p in required if p["category"] == "NON_TEXT"]
        results.append({"palette_id": palette["id"], "pairings": pairs,
                        "summary": {"required_pairs": len(required), "required_pair_failures": failures,
                                    "qualified_exempt_pairs": len(pairs) - len(required),
                                    "minimum_normal_text_ratio": min(text_ratios),
                                    "minimum_nontext_ratio": min(nontext_ratios)}})
    report = {
        "status": "OFFLINE_COLOR_PAIR_CALCULATION_ONLY",
        "algorithm": "WCAG 2.2 opaque sRGB luminance; 0.04045 channel threshold; exact threshold decision before display rounding",
        "input_sha256": hashlib.sha256(raw).hexdigest(), "arithmetic_checks": arithmetic_checks(),
        "sources": candidates["sources"], "limitations": candidates["pairing_policy"]["unsupported"],
        "results": results,
        "claim_boundary": "No screenshot, browser, font, keyboard, screen reader, Impeccable, full WCAG conformance or designer acceptance test was performed."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for result in results:
        summary = result["summary"]
        print(f"{result['palette_id']}: {summary['required_pairs']} applicable pairs; "
              f"{len(summary['required_pair_failures'])} below threshold; "
              f"{summary['qualified_exempt_pairs']} qualified exceptions; "
              f"minimum text {summary['minimum_normal_text_ratio']:.3f}; "
              f"minimum nontext {summary['minimum_nontext_ratio']:.3f}")
    return 1 if any(r["summary"]["required_pair_failures"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
