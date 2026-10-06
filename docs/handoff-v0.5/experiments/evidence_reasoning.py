#!/usr/bin/env python3
"""Synthetic evidence-policy lab; no model/provider calls and no runtime imports.

Typed atoms, source lineage, and oracle labels are HAND AUTHORED. This program
does not extract prose, infer causality, authenticate a real source, or measure
LLM hallucinations. It compares deliberately incomplete validation policies.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path
import platform
import time


@dataclass(frozen=True)
class Atom:
    subject: str
    predicate: str
    value: str
    period: str = "window-1"
    unit: str = "fact"

    def key(self):
        return self.subject, self.predicate, self.period, self.unit


@dataclass(frozen=True)
class Source:
    id: str
    atoms: tuple[Atom, ...]
    available: int = 90
    valid_from: int = 0
    valid_until: int = 120
    parents: tuple[str, ...] | None = ()
    origin_key: str | None = None
    kind: str = "OBSERVATION"
    authenticated: bool = True


@dataclass(frozen=True)
class Calculation:
    id: str
    operands: tuple[tuple[str, Atom], tuple[str, Atom]]
    result: str
    operation: str = "RATIO"


@dataclass(frozen=True)
class Claim:
    id: str
    kind: str
    atoms: tuple[Atom, ...] = ()
    source_ids: tuple[str, ...] = ()
    calculation_id: str | None = None
    depends_on: tuple[str, ...] = ()
    minimum_original_roots: int = 1
    baseline_count: int | None = None


@dataclass(frozen=True)
class Packet:
    sources: tuple[Source, ...]
    claims: tuple[Claim, ...]
    calculations: tuple[Calculation, ...] = ()
    cutoff: int = 100
    answer_override: str | None = None


@dataclass(frozen=True)
class Scenario:
    id: str
    description: str
    packet: Packet
    expected_graph_answer: str
    expected_accepted_ids: tuple[str, ...]
    unsupported_ids: tuple[str, ...] = ()
    world_false_ids: tuple[str, ...] = ()
    limit: str = ""


def eligible(source: Source, cutoff: int) -> bool:
    return (source.authenticated is True and source.available <= cutoff
            and source.valid_from <= cutoff <= source.valid_until)


def original_roots(sid: str, sources: dict[str, Source], cutoff: int, atom: Atom,
                   path=()) -> set[str]:
    """Known origin lineage, not the number of URLs/publishers or proof of truth."""
    if sid in path:
        raise ValueError("CIRCULAR_SOURCE_LINEAGE")
    source = sources.get(sid)
    if source is None:
        raise ValueError("MISSING_SOURCE_ANCESTOR")
    if source.authenticated is not True or source.available > cutoff:
        raise ValueError("INELIGIBLE_SOURCE_ANCESTOR")
    if atom not in source.atoms:
        raise ValueError("UNSUPPORTED_SOURCE_ANCESTOR")
    if source.parents is None:
        raise ValueError("UNKNOWN_ORIGIN_LINEAGE")
    if not source.parents:
        if source.origin_key is None:
            raise ValueError("UNKNOWN_ORIGIN_LINEAGE")
        return {source.origin_key}
    roots = set()
    for parent in source.parents:
        roots.update(original_roots(parent, sources, cutoff, atom, path + (sid,)))
    return roots


def dependency_error(cid: str, claims: dict[str, Claim], path=()) -> str | None:
    if cid in path:
        return "CIRCULAR_CLAIM_DEPENDENCY"
    if cid not in claims:
        return "MISSING_CLAIM_DEPENDENCY"
    for dep in claims[cid].depends_on:
        error = dependency_error(dep, claims, path + (cid,))
        if error:
            return error
    return None


def calculation_error(claim: Claim, packet: Packet, check_scope: bool) -> str | None:
    calculations = {x.id: x for x in packet.calculations}
    calculation = calculations.get(claim.calculation_id)
    if calculation is None or calculation.operation != "RATIO":
        return "MISSING_OR_UNSUPPORTED_CALCULATION"
    sources = {x.id: x for x in packet.sources}
    atoms = []
    for sid, atom in calculation.operands:
        source = sources.get(sid)
        if source is None or atom not in source.atoms:
            return "UNRESOLVED_OPERAND"
        if check_scope and not eligible(source, packet.cutoff):
            return "INELIGIBLE_OPERAND"
        atoms.append(atom)
    if check_scope and (atoms[0].unit != atoms[1].unit
                        or atoms[0].subject != atoms[1].subject
                        or atoms[0].period != atoms[1].period):
        return "OPERAND_SCOPE_OR_UNIT_MISMATCH"
    try:
        with localcontext() as ctx:
            ctx.prec = 50
            a, b = (Decimal(x.value) for x in atoms)
            result = Decimal(calculation.result)
            if not all(x.is_finite() for x in (a, b, result)) or b == 0:
                return "INVALID_NUMERIC_OPERAND"
            if a / b != result:
                return "INCORRECT_CALCULATION"
    except (InvalidOperation, ValueError, ArithmeticError):
        return "INVALID_NUMERIC_OPERAND"
    if check_scope:
        # A server-approved metric binds the operation AND operand meanings.
        # RATIO arithmetic alone cannot justify an arbitrary result predicate.
        if (tuple(a.predicate for a in atoms) != ("close", "prior_close")
                or len(claim.atoms) != 1
                or claim.atoms[0].predicate != "close_ratio"):
            return "UNAPPROVED_CALCULATION_METRIC"
        if (not set(sid for sid, _ in calculation.operands).issubset(claim.source_ids)
                or len(claim.atoms) != 1
                or claim.atoms[0].value != calculation.result
                or claim.atoms[0].subject != atoms[0].subject
                or claim.atoms[0].period != atoms[0].period
                or claim.atoms[0].unit != "ratio"):
            return "CLAIM_CALCULATION_MISMATCH"
    return None


def claim_reasons(claim: Claim, packet: Packet, profile: str) -> list[str]:
    sources = {x.id: x for x in packet.sources}
    if not claim.source_ids or any(sid not in sources for sid in claim.source_ids):
        return ["MISSING_SOURCE_ID"]
    if claim.kind == "DERIVED":
        error = calculation_error(claim, packet, profile != "EXISTENCE_ARITHMETIC")
        if error:
            return [error]
    if profile == "EXISTENCE_ARITHMETIC":
        return []
    candidates = [sources[sid] for sid in claim.source_ids
                  if eligible(sources[sid], packet.cutoff)]
    if not candidates:
        return ["NO_ELIGIBLE_SOURCE"]
    if claim.kind in {"CAUSAL", "ABSENCE"}:
        return ["CAUSAL_NOT_ESTABLISHED" if claim.kind == "CAUSAL"
                else "BOUNDED_SEARCH_IS_NOT_GLOBAL_ABSENCE"]
    if claim.kind not in {"FACT", "DERIVED", "ASSOCIATION", "ANOMALY"}:
        return ["UNKNOWN_CLAIM_KIND"]
    allowed_fact_predicates = {"close", "prior_close", "disclosure_published",
                               "access_restricted", "issuer_reports_cause"}
    if claim.kind != "DERIVED" and any(a.predicate not in allowed_fact_predicates
                                       for a in claim.atoms):
        return ["UNAPPROVED_FACT_PREDICATE"]
    if claim.kind == "ASSOCIATION" and (len(claim.atoms) < 2
             or len({(a.subject, a.period) for a in claim.atoms}) != 1):
        return ["MISALIGNED_ASSOCIATION"]
    if claim.kind == "ANOMALY" and (claim.baseline_count is None
                                    or claim.baseline_count < 20):
        return ["NO_APPROVED_BASELINE"]
    if claim.kind != "DERIVED":
        asserted = {atom for source in candidates for atom in source.atoms}
        if not claim.atoms or not set(claim.atoms).issubset(asserted):
            return ["UNSUPPORTED_TYPED_PREMISE"]
    # Contradiction policy here is conservative and handcrafted, not NLI.
    contradiction_atoms = claim.atoms
    if claim.kind == "DERIVED":
        calculation = next(x for x in packet.calculations if x.id == claim.calculation_id)
        contradiction_atoms += tuple(atom for _, atom in calculation.operands)
    for atom in contradiction_atoms:
        for source in packet.sources:
            if eligible(source, packet.cutoff) and any(
                    other.key() == atom.key() and other.value != atom.value
                    for other in source.atoms):
                return ["UNRESOLVED_CURRENT_CONTRADICTION"]
    if profile == "TYPED_SCOPE":
        return []
    error = dependency_error(claim.id, {x.id: x for x in packet.claims})
    if error:
        return [error]
    try:
        if claim.kind == "DERIVED":
            calculation = next(x for x in packet.calculations if x.id == claim.calculation_id)
            support_groups = [(atom, [sources[sid]]) for sid, atom in calculation.operands]
        else:
            # Only origins supporting the SAME atomic premise can corroborate it.
            # An unrelated citation is never a second confirmation of this atom.
            support_groups = [(atom, [source for source in candidates if atom in source.atoms])
                              for atom in claim.atoms]
        for atom, group in support_groups:
            roots = set()
            for source in group:
                roots.update(original_roots(source.id, sources, packet.cutoff, atom))
            if len(roots) < claim.minimum_original_roots:
                return ["INSUFFICIENT_DISTINCT_ORIGINS"]
    except ValueError as error:
        return [str(error)]
    return []


def render(claims: list[Claim]) -> str:
    # Closed lab templates forbid adding unvalidated prose to approved atoms.
    return "\n".join(f"[{claim.id}] " + "; ".join(
        f"{a.subject}/{a.predicate}={a.value} {a.unit} ({a.period})"
        for a in claim.atoms) for claim in claims)


def validate(packet: Packet, profile: str) -> dict:
    """No oracle/world truth is supplied to this function."""
    reasons = {claim.id: claim_reasons(claim, packet, profile)
               for claim in packet.claims}
    if profile == "GRAPH_RENDER":
        changed = True
        while changed:
            changed = False
            for claim in packet.claims:
                if not reasons[claim.id] and any(reasons.get(dep, ["missing"])
                                                  for dep in claim.depends_on):
                    reasons[claim.id] = ["UNSUPPORTED_CLAIM_DEPENDENCY"]
                    changed = True
    accepted = [c for c in packet.claims if not reasons[c.id]]
    expected_render = render(accepted)
    render_error = (profile == "GRAPH_RENDER" and packet.answer_override is not None
                    and packet.answer_override != expected_render)
    if render_error:
        answer = "REVIEW_REQUIRED"
        emitted = []
    elif not accepted:
        answer = "INSUFFICIENT_EVIDENCE"
        emitted = []
    else:
        answer = "ANSWERED" if len(accepted) == len(packet.claims) else "PARTIAL"
        emitted = [x.id for x in accepted]
    return {"answer_status": answer, "accepted_claim_ids": [x.id for x in accepted],
            "emitted_claim_ids": emitted, "claim_reasons": reasons,
            "render_error": "UNVALIDATED_MATERIAL_PROSE" if render_error else None,
            "rendered_lab_text": expected_render if not render_error else ""}


def fixtures() -> list[Scenario]:
    price = Atom("asset-A", "close", "120", unit="TRY")
    prior = Atom("asset-A", "prior_close", "100", unit="TRY")
    ratio = Atom("asset-A", "close_ratio", "1.2", unit="ratio")
    disclosure = Atom("asset-A", "disclosure_published", "yes")
    cause = Atom("asset-A", "disclosure_caused_return", "yes")
    restriction = Atom("fund-A", "access_restricted", "yes")
    unrestricted = replace(restriction, value="no")
    notice = Source("notice", (restriction,), kind="OFFICIAL", origin_key="regulator-decision")
    market = Source("market", (price, prior), origin_key="venue-observation")
    doc = Source("doc", (disclosure,), kind="OFFICIAL", origin_key="issuer-release")
    cprice = Claim("price", "FACT", (price,), ("market",))
    cratio = Claim("ratio", "DERIVED", (ratio,), ("market",), "ratio-1")
    calc = Calculation("ratio-1", (("market", price), ("market", prior)), "1.2")
    official = Claim("official", "FACT", (restriction,), ("notice",))
    wrong = Claim("wrong", "FACT", (replace(price, value="999"),), ("market",))
    cases = []
    def add(sid, description, packet, answer, accepted, unsupported=(), world_false=(), limit=""):
        cases.append(Scenario(sid, description, packet, answer, tuple(accepted),
                              tuple(unsupported), tuple(world_false), limit))
    add("E01", "Supported raw price fact", Packet((market,), (cprice,)), "ANSWERED", ["price"])
    add("E02", "Existing source ID with unsupported numeric premise", Packet((market,), (wrong,)),
        "INSUFFICIENT_EVIDENCE", [], ["wrong"])
    causal = Claim("cause", "CAUSAL", (cause,), ("market", "doc"))
    add("E03", "Correct ratio plus unsupported causal explanation",
        Packet((market, doc), (cratio, causal), (calc,)), "PARTIAL", ["ratio"], ["cause"])
    add("E04", "Incorrect computed ratio", Packet((market,), (replace(cratio, atoms=(replace(ratio, value="1.9"),)),),
        (replace(calc, result="1.9"),)), "INSUFFICIENT_EVIDENCE", [], ["ratio"])
    original = Source("original", (restriction,), origin_key="one-news-story")
    copy1 = Source("copy1", (restriction,), parents=("original",))
    copy2 = Source("copy2", (restriction,), parents=("original",))
    corroborated = Claim("corroborated", "FACT", (restriction,), ("copy1", "copy2"), minimum_original_roots=2)
    add("E05", "Two syndication copies are one origin",
        Packet((original, copy1, copy2), (corroborated,)), "INSUFFICIENT_EVIDENCE", [], ["corroborated"])
    independent1 = Source("i1", (restriction,), origin_key="independent-report-1")
    independent2 = Source("i2", (restriction,), origin_key="independent-report-2")
    independent = replace(corroborated, source_ids=("i1", "i2"))
    add("E06", "Independent reports agree but the hidden world oracle says false",
        Packet((independent1, independent2), (independent,)), "ANSWERED", ["corroborated"],
        world_false=["corroborated"], limit="Source-supported does not imply world-true; gate cannot discover the hidden falsehood.")
    a = Source("a", (restriction,), parents=("b",))
    b = Source("b", (restriction,), parents=("a",))
    add("E07", "Circular source citations without an original",
        Packet((a, b), (replace(official, source_ids=("a",)),)), "INSUFFICIENT_EVIDENCE", [], ["official"])
    cyc1 = replace(cprice, id="cyc1", depends_on=("cyc2",))
    cyc2 = replace(cprice, id="cyc2", depends_on=("cyc1",))
    add("E08", "Claim dependency cycle with individually cited atoms", Packet((market,), (cyc1, cyc2)),
        "INSUFFICIENT_EVIDENCE", [], ["cyc1", "cyc2"])
    add("E09", "Verified official access fact without any market baseline",
        Packet((notice,), (official,)), "ANSWERED", ["official"],
        limit="Verified factual notice needs identity/time/authenticity; a market anomaly baseline is irrelevant.")
    add("E10", "Official citation for the wrong fund", Packet((notice,),
        (replace(official, atoms=(replace(restriction, subject="fund-B"),)),)),
        "INSUFFICIENT_EVIDENCE", [], ["official"])
    stale = Source("stale", (unrestricted,), available=40, valid_until=80, origin_key="old-decision")
    add("E11", "Stale contradiction must not invalidate a current official fact",
        Packet((notice, stale), (official,)), "ANSWERED", ["official"])
    current_conflict = replace(stale, id="conflict", available=99, valid_until=120)
    add("E12", "Unresolved current contradiction", Packet((notice, current_conflict), (official,)),
        "INSUFFICIENT_EVIDENCE", [], ["official"])
    future = replace(notice, available=101)
    add("E13", "Publication unavailable at replay cutoff", Packet((future,), (official,)),
        "INSUFFICIENT_EVIDENCE", [], ["official"])
    add("E14", "Correct claim list with an omitted causal sentence in prose",
        Packet((market,), (cratio,), (calc,), answer_override=render([cratio]) + "\nThe issuer caused this rise."),
        "REVIEW_REQUIRED", ["ratio"], limit="Only a closed renderer makes complete material-sentence coverage mechanical; no free-prose classifier was tested.")
    absence = Claim("absence", "ABSENCE", (Atom("asset-A", "no_news_exists", "yes"),), ("doc",))
    add("E15", "Bounded search result promoted to no news anywhere", Packet((doc,), (absence,)),
        "INSUFFICIENT_EVIDENCE", [], ["absence"])
    add("E16", "No usable evidence", Packet((), (replace(cprice, source_ids=()),)),
        "INSUFFICIENT_EVIDENCE", [], ["price"])
    report_atom = Atom("asset-A", "issuer_reports_cause", "disclosure")
    attributed = Source("attributed", (report_atom,), kind="OFFICIAL", origin_key="issuer-comment")
    add("E17", "Attribution is a fact; the attributed cause is not established",
        Packet((attributed,), (Claim("attribution", "FACT", (report_atom,), ("attributed",)),)),
        "ANSWERED", ["attribution"])
    usd_prior = replace(prior, unit="USD")
    unit_market = replace(market, atoms=(price, usd_prior))
    unit_calc = replace(calc, operands=(("market", price), ("market", usd_prior)))
    add("E18", "Numerically correct ratio with mixed currencies",
        Packet((unit_market,), (cratio,), (unit_calc,)), "INSUFFICIENT_EVIDENCE", [], ["ratio"])
    association = Claim("association", "ASSOCIATION", (price, disclosure), ("market", "doc"))
    add("E19", "Two factual observations in one window without causal promotion",
        Packet((market, doc), (association,)), "ANSWERED", ["association"])
    failed_parent = replace(cprice, id="child", depends_on=("wrong",))
    add("E20", "Directly supported child depends on a rejected material premise",
        Packet((market,), (wrong, failed_parent)), "INSUFFICIENT_EVIDENCE", [], ["wrong", "child"])
    unknown = replace(notice, parents=None, origin_key=None)
    add("E21", "Unknown origin cannot assert independent corroboration",
        Packet((unknown,), (official,)), "INSUFFICIENT_EVIDENCE", [], ["official"])
    zero = replace(prior, value="0")
    zero_source = replace(market, atoms=(price, zero))
    zero_calc = replace(calc, operands=(("market", price), ("market", zero)))
    add("E22", "Zero denominator", Packet((zero_source,), (cratio,), (zero_calc,)),
        "INSUFFICIENT_EVIDENCE", [], ["ratio"])
    add("E23", "Raw fact promoted to anomaly without reference history",
        Packet((market,), (replace(cprice, kind="ANOMALY", baseline_count=0),)),
        "INSUFFICIENT_EVIDENCE", [], ["price"])
    add("E24", "High score cannot repair unauthenticated official evidence",
        Packet((replace(notice, authenticated=False),), (official,)),
        "INSUFFICIENT_EVIDENCE", [], ["official"])
    asserting_cause = Source("causal_source", (cause,), origin_key="issuer-assertion")
    add("E25", "Causal proposition laundered through the FACT label",
        Packet((asserting_cause,), (Claim("laundered", "FACT", (cause,), ("causal_source",)),)),
        "INSUFFICIENT_EVIDENCE", [], ["laundered"],
        limit="A server-owned predicate registry, not the model's FACT label, supplies the lab distinction.")
    future_original = replace(original, available=101)
    add("E26", "Eligible-looking copy has a future original ancestor",
        Packet((future_original, copy1), (replace(official, source_ids=("copy1",)),)),
        "INSUFFICIENT_EVIDENCE", [], ["official"])
    old_disclosure = replace(disclosure, period="window-0")
    old_doc = replace(doc, atoms=(old_disclosure,))
    add("E27", "Individually supported facts combined as misaligned temporal association",
        Packet((market, old_doc), (replace(association, atoms=(price, old_disclosure)),)),
        "INSUFFICIENT_EVIDENCE", [], ["association"])
    add("E28", "Unrelated citation cannot pad corroboration origins for a premise",
        Packet((notice, doc), (replace(official, source_ids=("notice", "doc"),
                                     minimum_original_roots=2),)),
        "INSUFFICIENT_EVIDENCE", [], ["official"])
    add("E29", "Correct ratio cannot license a causal result predicate",
        Packet((market,), (replace(cratio, atoms=(replace(ratio, predicate="disclosure_caused_ratio"),)),),
               (calc,)), "INSUFFICIENT_EVIDENCE", [], ["ratio"])
    other_price = replace(price, value="125")
    reverse_market = replace(market, atoms=(other_price, prior))
    reverse_calc = replace(calc, operands=(("market", prior), ("market", other_price)), result="0.8")
    add("E30", "Correct arithmetic with reversed metric operands",
        Packet((reverse_market,), (replace(cratio, atoms=(replace(ratio, value="0.8"),)),),
               (reverse_calc,)), "INSUFFICIENT_EVIDENCE", [], ["ratio"])
    unsupported_copy = Source("unsupported_copy", (restriction,), parents=("doc",))
    add("E31", "Cited ancestor does not assert the copied premise",
        Packet((doc, unsupported_copy), (replace(official, source_ids=("unsupported_copy",)),)),
        "INSUFFICIENT_EVIDENCE", [], ["official"],
        limit="The check uses supplied atomic assertions; real quotation/paraphrase lineage extraction is not tested.")
    conflicting_price = Source("price_conflict", (replace(price, value="130"),),
                               origin_key="conflicting-venue-record")
    add("E32", "Correct calculation depends on a currently contradicted operand",
        Packet((market, conflicting_price), (cratio,), (calc,)),
        "INSUFFICIENT_EVIDENCE", [], ["ratio"])
    return cases


@dataclass(frozen=True)
class Stage:
    name: str
    calls: int = 1
    searches: int = 0
    sources: int = 0
    reserved_tokens: int = 0
    simulated_ms: int = 0


def budget_simulation(stages: list[Stage], caps: dict) -> dict:
    used = dict.fromkeys(caps, 0)
    accepted = []
    for stage in stages:
        values = {key: getattr(stage, key) for key in caps}
        exceeded = [key for key, cap in caps.items() if used[key] + values[key] > cap]
        if exceeded:
            return {"accepted_stages": accepted, "rejected_before_call": stage.name,
                    "exceeded": exceeded, "used": used, "caps": caps}
        used = {key: used[key] + values[key] for key in caps}
        accepted.append(stage.name)
    return {"accepted_stages": accepted, "rejected_before_call": None,
            "exceeded": [], "used": used, "caps": caps}


def run() -> dict:
    started = time.perf_counter()
    cases = fixtures()
    profiles = ("EXISTENCE_ARITHMETIC", "TYPED_SCOPE", "GRAPH_RENDER")
    rows = []
    for case in cases:
        outcomes = {profile: validate(case.packet, profile) for profile in profiles}
        graph = outcomes["GRAPH_RENDER"]
        matches = (graph["answer_status"] == case.expected_graph_answer
                   and graph["accepted_claim_ids"] == list(case.expected_accepted_ids))
        rows.append({"id": case.id, "description": case.description,
                     "input": asdict(case.packet),
                     "oracle": {"graph_answer": case.expected_graph_answer,
                                "accepted_ids": list(case.expected_accepted_ids),
                                "unsupported_ids": list(case.unsupported_ids),
                                "world_false_ids": list(case.world_false_ids)},
                     "outcomes": outcomes, "graph_policy_oracle_match": matches,
                     "limit": case.limit})
    summary = {}
    for profile in profiles:
        unsupported = []
        world_false = []
        emitted = 0
        for case, row in zip(cases, rows):
            outcome = row["outcomes"][profile]
            emitted += len(outcome["emitted_claim_ids"])
            unsupported += [f"{case.id}:{cid}" for cid in outcome["emitted_claim_ids"]
                            if cid in case.unsupported_ids]
            world_false += [f"{case.id}:{cid}" for cid in outcome["emitted_claim_ids"]
                            if cid in case.world_false_ids]
        summary[profile] = {"answer_status_counts": dict(Counter(
            r["outcomes"][profile]["answer_status"] for r in rows)),
            "emitted_claim_count": emitted,
            "unsupported_fixture_claims_emitted": unsupported,
            "known_world_false_but_source_supported_claims_emitted": world_false,
            "unvalidated_prose_cases_published": [r["id"] for r in rows
                 if r["input"]["answer_override"] is not None
                 and r["outcomes"][profile]["answer_status"] != "REVIEW_REQUIRED"]}
    caps = {"calls": 6, "searches": 2, "sources": 8,
            "reserved_tokens": 8000, "simulated_ms": 45000}
    basic = [Stage("internal_retrieve", sources=3, simulated_ms=100),
             Stage("extract_draft", reserved_tokens=2000, simulated_ms=4000),
             Stage("targeted_search", searches=1, sources=3, simulated_ms=6000),
             Stage("calculate", simulated_ms=20),
             Stage("review_material_claims", reserved_tokens=1400, simulated_ms=3000)]
    plans = {"bounded_retrieve_extract_review": budget_simulation(basic, caps),
             "repeated_self_checks": budget_simulation(basic + [
                 Stage(f"self_check_{i}", reserved_tokens=1400, simulated_ms=3000)
                 for i in range(1, 21)], caps),
             "third_search": budget_simulation([
                 Stage(f"search_{i}", searches=1, sources=2, simulated_ms=6000)
                 for i in range(1, 4)], caps),
             "source_overrun": budget_simulation([Stage("retrieve_nine_sources", sources=9)], caps),
             "timeout_reservation": budget_simulation([Stage("slow_fetch", simulated_ms=45001)], caps)}
    budget_assertions = {
        "bounded_plan_fits": plans["bounded_retrieve_extract_review"]["rejected_before_call"] is None,
        "seventh_call_rejected": plans["repeated_self_checks"]["rejected_before_call"] == "self_check_2",
        "third_search_rejected": plans["third_search"]["rejected_before_call"] == "search_3",
        "ninth_source_rejected": plans["source_overrun"]["rejected_before_call"] is not None,
        "timeout_rejected": plans["timeout_reservation"]["rejected_before_call"] is not None}
    score = int((Decimal(100) * sum((Decimal(w) for w in ("0.35", "0.25", "0.25", "0.15")),
                                  Decimal(0))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    result = {"schema_version": "evidence-lab-v1", "origin": "SYNTHETIC",
              "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "seed": None, "determinism": "Hand-authored fixtures; no stochastic generation.",
              "requirements": ["FR-055", "FR-057", "FR-058", "FR-061", "FR-067", "FR-068",
                               "FR-096", "FR-097", "NFR-026", "NFR-027", "NFR-028", "NFR-029", "NFR-031", "NFR-081"],
              "case_count": len(rows), "graph_policy_oracle_matches": sum(r["graph_policy_oracle_match"] for r in rows),
              "summary": summary, "cases": rows,
              "budget_plans": plans, "budget_assertions": budget_assertions,
              "budget_semantics": "Conservative combined stage-call cap is a laboratory proposal; the existing tool-call cap alone does not cap model requests. Reserved tokens and milliseconds are invented caps, not measured consumption.",
              "score_counterexample": {"case": "E06", "components": {"Q": 1, "F": 1, "I": 1, "C": 1},
                  "heuristic_score": score, "calibrated_probability": None,
                  "world_truth_oracle": False, "interpretation": "Perfect rubric components can coexist with a world-false assertion."},
              "limitations": ["No LLM, NLI, provider, real document, customer or market evaluation.",
                  "Typed atoms/authentication/time/provenance are manually supplied, not established by this experiment.",
                  "Known origin count prevents duplicate counting; it is not statistical/causal independence or source truth.",
                  "The closed renderer avoids unlisted prose; arbitrary natural-language entailment remains untested.",
                  "Budget durations/tokens are invented scenario reservations, not actual model latency or measured expenditure.",
                  "No USD/TRY price, real hallucination rate, precision, calibration or financial benefit is inferred."],
              "external_calls_executed": 0, "paid_runtime_cost": 0,
              "actual_model_latency_ms": None, "actual_model_token_usage": None,
              "wall_seconds_local": round(time.perf_counter() - started, 6)}
    result["passed"] = result["graph_policy_oracle_matches"] == len(rows) and all(budget_assertions.values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("research/engine_lab/evidence_results.json"))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"origin": result["origin"], "cases": result["case_count"],
                      "graph_policy_oracle_matches": result["graph_policy_oracle_matches"],
                      "budget_assertions": result["budget_assertions"],
                      "summary": result["summary"], "passed": result["passed"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
