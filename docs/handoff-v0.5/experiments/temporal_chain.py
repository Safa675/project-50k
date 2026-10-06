#!/usr/bin/env python3
"""Deterministic SYNTHETIC temporal/chain experiment; standard library only.

Not an RPC client, consensus verifier, production outbox, economic trade parser,
beneficial-owner resolver or empirical market evaluation. No network/send code.
Run from package root: python experiments/temporal_chain.py --output \
research/engine_lab/temporal_chain_results.json
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random

DAY = "2026-10-01"
CONFIG = {"version": "temporal-chain-lab-v1", "rvol_threshold": "3", "chain_delivery_minimum": "FINALIZED"}
ADMITTED_STATES = {"MARKET": {"ACTIVE"}, "DOCUMENT": {"ACTIVE"},
                   "CHAIN": {"PROVISIONAL", "PROCESSED", "CONFIRMED", "FINALIZED"}}


def instant(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Naive timestamp is not permitted")
    return result.astimezone(timezone.utc)


def at(clock: str) -> str:
    return f"{DAY}T{clock}:00Z"


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Record:
    key: str
    revision: int
    kind: str
    asset: str
    effective_at: str
    published_at: str | None
    available_at: str
    ingested_at: str
    availability_provenance: str
    state: str
    network: str | None
    block_ref: str | None
    values: tuple[tuple[str, str], ...]
    origin: str = "SYNTHETIC"

    def payload(self) -> dict:
        value = asdict(self)
        value["values"] = dict(self.values)
        return value


def row(key: str, revision: int, kind: str, asset: str, effective: str,
        available: str, ingested: str, values: dict[str, str], *,
        published: str | None = None, provenance: str = "OBSERVED",
        state: str = "ACTIVE", network: str | None = None,
        block_ref: str | None = None) -> Record:
    return Record(key, revision, kind, asset, at(effective), at(published) if published else None,
                  at(available), at(ingested), provenance, state, network, block_ref,
                  tuple(sorted(values.items())))


def eligible(record: Record, cutoff: str, basis: str) -> bool:
    if basis not in {"SOURCE_AVAILABLE_RECONSTRUCTION", "ACTUALLY_INGESTED"}:
        raise ValueError("Unknown replay basis")
    limit = instant(cutoff)
    if record.availability_provenance not in {"OBSERVED", "ARCHIVE_VERIFIED"}:
        return False
    if instant(record.available_at) > limit:
        return False
    if record.published_at and instant(record.published_at) > limit:
        return False
    if basis == "ACTUALLY_INGESTED" and instant(record.ingested_at) > limit:
        return False
    # Announced future-effective documents can be valid evidence of an upcoming
    # event. Future numerical observations cannot become present observations.
    if record.kind in {"MARKET", "CHAIN"} and instant(record.effective_at) > limit:
        return False
    return True


def snapshot(records: list[Record], cutoff: str, basis: str) -> tuple[list[Record], list[dict]]:
    """Select latest eligible revision per source key, independent of arrival order.

    A conflicting same-key/revision identity is quarantined, not last-write-wins.
    This small model assumes a provider's revision numbers monotonically describe
    versions; production adapters must establish that guarantee explicitly.
    """
    identities: dict[tuple[str, int], dict[str, Record]] = {}
    for record in records:
        if eligible(record, cutoff, basis):
            identities.setdefault((record.key, record.revision), {})[digest(record.payload())] = record
    conflicts = [{"key": key, "revision": rev, "reason": "CONFLICTING_IDENTITY_PAYLOAD"}
                 for (key, rev), payloads in sorted(identities.items()) if len(payloads) != 1]
    poisoned_keys = {entry["key"] for entry in conflicts}
    candidates = [next(iter(payloads.values())) for (key, _), payloads in identities.items()
                  if len(payloads) == 1 and key not in poisoned_keys]
    selected: dict[str, Record] = {}
    for record in candidates:
        if record.key not in selected or record.revision > selected[record.key].revision:
            selected[record.key] = record
    return [selected[key] for key in sorted(selected)], conflicts


def freeze(records: list[Record], cutoff: str, basis: str, config: dict = CONFIG) -> dict:
    chosen, conflicts = snapshot(records, cutoff, basis)
    payload = {"format": "synthetic-bundle-v1", "cutoff": cutoff, "basis": basis,
               "config": dict(config), "records": [record.payload() for record in chosen],
               "conflicts": conflicts, "origin": "SYNTHETIC"}
    # Detached serialized content means later mutations/appends cannot alter it.
    return {"bundle_hash": digest(payload), "content_json": canonical(payload)}


def verify(bundle: dict) -> bool:
    return digest(json.loads(bundle["content_json"])) == bundle["bundle_hash"]


def get(records: list[Record], key: str) -> Record | None:
    return next((record for record in records if record.key == key), None)


def rvol(record: Record | dict | None, config: dict) -> dict:
    payload = record.payload() if isinstance(record, Record) else record
    if payload is None or payload["state"] != "ACTIVE":
        return {"outcome": "ABSTAINED", "reason": "MISSING_OR_RETRACTED"}
    values = payload["values"]
    ratio = Decimal(values["volume"]) / Decimal(values["prior_slot_median"])
    threshold = Decimal(config["rvol_threshold"])
    return {"outcome": "CANDIDATE" if ratio >= threshold else "NOT_FLAGGED",
            "ratio": str(ratio), "threshold": str(threshold), "evidence_revision": payload["revision"],
            "note": "Constructed arithmetic only; no empirically validated threshold."}


def score_bundle(bundle: dict, key: str) -> dict:
    if not verify(bundle):
        raise ValueError("Bundle content hash does not match")
    payload = json.loads(bundle["content_json"])
    record = next((record for record in payload["records"] if record["key"] == key), None)
    return rvol(record, payload["config"])


def naive_current_row(records: list[Record]) -> list[Record]:
    current: dict[str, Record] = {}
    for record in records:
        if record.key not in current or record.revision > current[record.key].revision:
            current[record.key] = record
    return [current[key] for key in sorted(current)]


def naive_last_arrival(records: list[Record]) -> list[Record]:
    current = {record.key: record for record in records}
    return [current[key] for key in sorted(current)]


def local_delivery_gate(record: Record | None, expected_revision: int,
                        expected_hash: str, *, require_finalized: bool) -> tuple[bool, str]:
    if record is None:
        return False, "MISSING_EVIDENCE"
    if record.revision != expected_revision or digest(record.payload()) != expected_hash:
        return False, "STALE_REVISION_OR_PAYLOAD"
    if record.state not in ADMITTED_STATES.get(record.kind, set()):
        return False, "STATE_NOT_ADMITTED"
    if require_finalized and record.state != "FINALIZED":
        return False, "NOT_FINALIZED"
    return True, "ELIGIBLE_FOR_LOCAL_DRY_RUN_ONLY"


def intent_transition(dependency: Record, current: Record | None, state: str,
                      *, require_finalized: bool) -> dict:
    okay, reason = local_delivery_gate(current, dependency.revision,
                                       digest(dependency.payload()), require_finalized=require_finalized)
    if okay:
        after = "SIMULATED_ACCEPTED" if state == "QUEUED" else state
    elif state == "SIMULATED_ACCEPTED":
        after = "CORRECTION_REQUIRED"
    else:
        after = "SUPPRESSED"
    return {"before": state, "after": after, "reason": reason,
            "dependency_key": dependency.key, "dependency_revision": dependency.revision,
            "current_revision": current.revision if current else None,
            "external_send": False, "channel": "LOCAL_DRY_RUN"}


def fixtures() -> list[Record]:
    market_v1 = row("bist-demo:volume-bar-0900", 1, "MARKET", "BIST_DEMO",
                    "09:00", "10:00", "10:01", {"volume": "600", "prior_slot_median": "100"}, published="10:00")
    market_v2 = row(market_v1.key, 2, "MARKET", "BIST_DEMO",
                    "09:00", "10:05", "10:05", {"volume": "120", "prior_slot_median": "100"}, published="10:05")
    disclosure = row("issuer-demo:notice-01", 1, "DOCUMENT", "BIST_DEMO",
                     "10:02", "10:02", "10:07", {"classification": "ISSUER_NOTICE"}, published="10:02")
    backfill = row("archive-demo:bar-0930", 1, "MARKET", "BIST_DEMO",
                   "09:30", "09:31", "10:08", {"volume": "100", "prior_slot_median": "100"},
                   published="09:31", provenance="ARCHIVE_VERIFIED")
    unknown = row("unknown-demo:history-01", 1, "DOCUMENT", "BIST_DEMO",
                  "08:00", "08:00", "10:08", {"classification": "UNVERIFIED_BACKFILL"}, provenance="UNKNOWN")
    future_document = row("issuer-demo:future-effective-01", 1, "DOCUMENT", "BIST_DEMO",
                          "11:00", "10:02", "10:02", {"classification": "UPCOMING_ACTION"}, published="10:02")
    ethereum_a1 = row("evm:1:tx-A:log-0:block-A", 1, "CHAIN", "TOKEN_DEMO",
                      "10:02", "10:02", "10:02", {"raw_amount": "1000000000"},
                      state="PROVISIONAL", network="evm:1", block_ref="block-A:height-100")
    ethereum_a2 = row(ethereum_a1.key, 2, "CHAIN", "TOKEN_DEMO",
                      "10:02", "10:04", "10:04", {"raw_amount": "1000000000"},
                      state="ORPHANED", network="evm:1", block_ref="block-A:height-100")
    ethereum_b1 = row("evm:1:tx-B:log-0:block-B", 1, "CHAIN", "TOKEN_DEMO",
                      "10:04", "10:04", "10:04", {"raw_amount": "500000000"},
                      state="PROVISIONAL", network="evm:1", block_ref="block-B:height-100")
    ethereum_b2 = row(ethereum_b1.key, 2, "CHAIN", "TOKEN_DEMO",
                      "10:04", "10:08", "10:08", {"raw_amount": "500000000"},
                      state="FINALIZED", network="evm:1", block_ref="block-B:height-100")
    solana_1 = row("solana:DEMO_GENESIS:signature-S:instruction-0:slot-501", 1, "CHAIN", "TOKEN_DEMO",
                   "10:02", "10:02", "10:02", {"raw_amount": "700000000"},
                   state="PROCESSED", network="solana:DEMO_GENESIS", block_ref="slot-501:block-S")
    solana_2 = row(solana_1.key, 2, "CHAIN", "TOKEN_DEMO",
                   "10:02", "10:03", "10:03", {"raw_amount": "700000000"},
                   state="CONFIRMED", network="solana:DEMO_GENESIS", block_ref="slot-501:block-S")
    solana_3 = row(solana_1.key, 3, "CHAIN", "TOKEN_DEMO",
                   "10:02", "10:05", "10:05", {"raw_amount": "700000000"},
                   state="FINALIZED", network="solana:DEMO_GENESIS", block_ref="slot-501:block-S")
    # An old exact duplicate arrives after the revision, with its original
    # provenance timestamps. Receipt order is a separate transport concern.
    return [market_v1, ethereum_a1, solana_1, future_document, solana_2,
            ethereum_a2, ethereum_b1, market_v2, solana_3, disclosure,
            backfill, unknown, ethereum_b2, market_v1]


def semantics() -> dict:
    accounts = [
        {"address": "token-A1", "program_owner": "SPL_TOKEN_PROGRAM_DEMO", "token_authority": "authority-W1", "mint": "MINT_DEMO", "raw_balance": "400"},
        {"address": "token-A2", "program_owner": "SPL_TOKEN_PROGRAM_DEMO", "token_authority": "authority-W1", "mint": "MINT_DEMO", "raw_balance": "300"},
        {"address": "token-A3", "program_owner": "SPL_TOKEN_PROGRAM_DEMO", "token_authority": "authority-W2", "mint": "MINT_DEMO", "raw_balance": "200"},
        {"address": "token-A4", "program_owner": "SPL_TOKEN_PROGRAM_DEMO", "token_authority": "authority-PDA_OR_MULTISIG", "mint": "MINT_DEMO", "raw_balance": "100"},
    ]
    return {"origin": "SYNTHETIC", "erc20_transfer": {"network": "evm:1", "contract": "TOKEN_CONTRACT_DEMO", "transaction": "tx-B", "log_index": 0,
                "from": "address-X", "to": "address-Y", "raw_amount": "500000000",
                "token_decimals": None, "human_token_amount": None, "monetary_notional": None,
                "sale_status": "NOT_ESTABLISHED", "beneficial_owner_from": None, "beneficial_owner_to": None,
                "statement_tr": "Örnek zincir kaydında bir token transferi görülüyor. Satış ve gerçek kişi sahipliği bu kayıttan belirlenemez."},
            "compatible_but_unproven_contexts": ["custody movement", "exchange deposit without sale", "settlement of a separately verified trade"],
            "solana_token_accounts": accounts, "naive_beneficial_owner_count": len(accounts),
            "distinct_direct_token_authorities": len({x["token_authority"] for x in accounts}),
            "program_owners": sorted({x["program_owner"] for x in accounts}), "beneficial_owner_count": None,
            "authority_aggregation": {"authority-W1": "700", "authority-W2": "200", "authority-PDA_OR_MULTISIG": "100"},
            "boundary": "Authority/address concentration is observable in this complete toy mint snapshot; person/cluster ownership is unresolved. Real largest-account RPC coverage is partial unless all accounts and supply semantics are established."}


def run() -> dict:
    records = fixtures()
    cutoff = at("10:03")
    initial = [x for x in records if instant(x.ingested_at) <= instant(cutoff)]
    actual, _ = snapshot(records, cutoff, "ACTUALLY_INGESTED")
    reconstructed, _ = snapshot(records, cutoff, "SOURCE_AVAILABLE_RECONSTRUCTION")
    current = naive_current_row(records)
    arrival = naive_last_arrival(records)
    old_bundle = freeze(initial, cutoff, "ACTUALLY_INGESTED")
    later_same = freeze(records, cutoff, "ACTUALLY_INGESTED")
    reconstructed_before = freeze(initial, cutoff, "SOURCE_AVAILABLE_RECONSTRUCTION")
    reconstructed_after = freeze(records, cutoff, "SOURCE_AVAILABLE_RECONSTRUCTION")
    later, _ = snapshot(records, at("10:09"), "ACTUALLY_INGESTED")
    mk = records[0].key
    ak = "evm:1:tx-A:log-0:block-A"
    bk = "evm:1:tx-B:log-0:block-B"
    sk = "solana:DEMO_GENESIS:signature-S:instruction-0:slot-501"
    reorg_snapshot, _ = snapshot(records, at("10:04"), "ACTUALLY_INGESTED")
    chain_pre = get(actual, ak)
    chain_orphan = get(reorg_snapshot, ak)
    finalized_b = get(later, bk)
    solana_confirmed = get(actual, sk)
    finalized_s = get(later, sk)
    transitions = [
        intent_transition(get(actual, mk), get(later, mk), "QUEUED", require_finalized=False),
        intent_transition(chain_pre, chain_orphan, "QUEUED", require_finalized=True),
        intent_transition(chain_pre, chain_orphan, "SIMULATED_ACCEPTED", require_finalized=True),
        intent_transition(solana_confirmed, solana_confirmed, "QUEUED", require_finalized=True),
        intent_transition(finalized_b, finalized_b, "QUEUED", require_finalized=True),
        intent_transition(finalized_s, finalized_s, "QUEUED", require_finalized=True),
    ]
    wrong_hash_gate = local_delivery_gate(finalized_b, finalized_b.revision, "0" * 64, require_finalized=True)
    denied_state_gates = []
    for state in ["RETRACTED", "INVALIDATED", "UNKNOWN", "ORPHANED"]:
        # Dependency/current are identical here, so this isolates state rejection
        # from stale-revision protection, with finality policy deliberately off.
        withdrawn = replace(get(actual, mk), state=state)
        okay, reason = local_delivery_gate(withdrawn, withdrawn.revision,
                                           digest(withdrawn.payload()), require_finalized=False)
        denied_state_gates.append({"state": state, "allowed": okay, "reason": reason})
    wrong_kind_states = [replace(get(actual, mk), state="FINALIZED"), replace(finalized_b, state="ACTIVE")]
    kind_state_gates = [{"kind": record.kind, "state": record.state,
                        "allowed": local_delivery_gate(record, record.revision, digest(record.payload()), require_finalized=False)[0]}
                       for record in wrong_kind_states]
    alternate_policy_bundle = freeze(initial, cutoff, "ACTUALLY_INGESTED", dict(CONFIG, rvol_threshold="7"))
    conflicting = row(mk, 2, "MARKET", "BIST_DEMO", "09:00", "10:05", "10:05", {"volume": "9000", "prior_slot_median": "100"}, published="10:05")
    collision_snapshot, collision_notes = snapshot(records + [conflicting], at("10:09"), "ACTUALLY_INGESTED")
    altered = json.loads(old_bundle["content_json"])
    altered["records"][0]["revision"] = 99
    tampered = dict(old_bundle, content_json=canonical(altered))
    reorder_rng = random.Random(50_000)
    robust_same = 0
    naive_revision_rollbacks = 0
    for _ in range(100):
        shuffled = records[:]
        reorder_rng.shuffle(shuffled)
        robust_same += freeze(shuffled, at("10:09"), "ACTUALLY_INGESTED")["bundle_hash"] == freeze(records, at("10:09"), "ACTUALLY_INGESTED")["bundle_hash"]
        naive_revision_rollbacks += get(naive_last_arrival(shuffled), mk).revision == 1
    sem = semantics()
    checks = [
        ("C01_future_revision_excluded", get(actual, mk).revision == 1),
        ("C02_current_rows_change_past_signal", score_bundle(old_bundle, mk)["outcome"] == "CANDIDATE" and rvol(get(current, mk), CONFIG)["outcome"] == "NOT_FLAGGED"),
        ("C03_late_original_cannot_roll_back_current_revision", get(later, mk).revision == 2 and get(arrival, mk).revision == 1),
        ("C04_late_available_document_not_claimed_actually_ingested", get(actual, "issuer-demo:notice-01") is None and get(reconstructed, "issuer-demo:notice-01") is not None),
        ("C05_archived_backfill_basis_is_explicit", get(actual, "archive-demo:bar-0930") is None and get(reconstructed, "archive-demo:bar-0930") is not None),
        ("C06_unknown_availability_excluded", get(reconstructed, "unknown-demo:history-01") is None),
        ("C07_frozen_actual_bundle_unchanged", old_bundle["bundle_hash"] == later_same["bundle_hash"] and verify(old_bundle)),
        ("C08_new_archival_evidence_requires_distinct_bundle", reconstructed_before["bundle_hash"] != reconstructed_after["bundle_hash"]),
        ("C09_content_tampering_detected", not verify(tampered)),
        ("C10_conflicting_revision_quarantined", get(collision_snapshot, mk) is None and len(collision_notes) == 1),
        ("C11_reorg_cancels_pending_evidence_intent", transitions[1]["after"] == "SUPPRESSED"),
        ("C12_already_accepted_requires_correction", transitions[2]["after"] == "CORRECTION_REQUIRED"),
        ("C13_confirmed_is_not_finalized", transitions[3]["after"] == "SUPPRESSED"),
        ("C14_finalized_evidence_local_dry_run_only", all(x["after"] == "SIMULATED_ACCEPTED" and not x["external_send"] for x in transitions[4:])),
        ("C15_payload_hash_mismatch_blocks", not wrong_hash_gate[0]),
        ("C16_revision_cancels_stale_market_intent", transitions[0]["after"] == "SUPPRESSED"),
        ("C17_reordering_invariant", robust_same == 100 and naive_revision_rollbacks > 0),
        ("C18_transfer_does_not_establish_sale", sem["erc20_transfer"]["sale_status"] == "NOT_ESTABLISHED"),
        ("C19_token_accounts_are_not_people", sem["naive_beneficial_owner_count"] != sem["distinct_direct_token_authorities"] and sem["beneficial_owner_count"] is None),
        ("C20_future_effective_notice_retained_as_upcoming", get(actual, "issuer-demo:future-effective-01") is not None),
        ("C21_missing_decimals_prevents_amount_notional", sem["erc20_transfer"]["human_token_amount"] is None and sem["erc20_transfer"]["monetary_notional"] is None),
        ("C22_policy_config_part_of_bundle_identity", old_bundle["bundle_hash"] != freeze(initial, cutoff, "ACTUALLY_INGESTED", dict(CONFIG, rvol_threshold="4"))["bundle_hash"]),
        ("C23_stored_policy_controls_frozen_score", score_bundle(old_bundle, mk)["outcome"] == "CANDIDATE" and score_bundle(alternate_policy_bundle, mk)["outcome"] == "NOT_FLAGGED" and score_bundle(alternate_policy_bundle, mk)["threshold"] == "7"),
        ("C24_retracted_self_binding_blocks_without_finality_gate", not denied_state_gates[0]["allowed"]),
        ("C25_invalidated_self_binding_blocks_without_finality_gate", not denied_state_gates[1]["allowed"]),
        ("C26_unknown_self_binding_blocks_without_finality_gate", not denied_state_gates[2]["allowed"]),
        ("C27_orphaned_self_binding_blocks_without_finality_gate", not denied_state_gates[3]["allowed"]),
        ("C28_future_finalization_does_not_leak_to_cutoff", solana_confirmed.state == "CONFIRMED" and chain_pre.state == "PROVISIONAL" and get(actual, bk) is None),
        ("C29_kind_state_mismatch_blocks", all(not case["allowed"] for case in kind_state_gates)),
    ]
    if not all(result for _, result in checks):
        raise AssertionError([name for name, passed in checks if not passed])
    return {"experiment": "temporal-chain-lab-v1", "origin": "SYNTHETIC", "seed": 50_000,
            "scope": "Deterministic local event-log/snapshot and dry-run state experiment; no RPC, live market data, email, deployed consensus or production concurrency.",
            "input_hash": digest([record.payload() for record in records]), "config": CONFIG,
            "checks": [{"id": name, "passed": passed} for name, passed in checks],
            "summary": {"passed": sum(passed for _, passed in checks), "total": len(checks), "records_including_duplicate": len(records),
                        "unique_key_revision_pairs": len({(record.key, record.revision) for record in records}),
                        "actual_ingested_record_count_at_cutoff": len(actual), "source_available_reconstruction_record_count_at_cutoff": len(reconstructed),
                        "shuffle_trials": 100, "guarded_snapshot_same_hash_trials": robust_same,
                        "naive_last_arrival_revision_rollback_trials": naive_revision_rollbacks, "external_sends": 0},
            "historical_comparison": {"cutoff": cutoff, "actual_signal": score_bundle(old_bundle, mk), "naive_current_row_signal_for_past": rvol(get(current, mk), CONFIG),
                "naive_last_arrival_current_signal": rvol(get(arrival, mk), CONFIG), "guarded_current_signal": rvol(get(later, mk), CONFIG),
                "actual_keys": [record.key for record in actual], "source_available_reconstruction_keys": [record.key for record in reconstructed],
                "actual_bundle_hash": old_bundle["bundle_hash"], "same_actual_bundle_after_late_records_hash": later_same["bundle_hash"],
                "archival_bundle_before_backfill_hash": reconstructed_before["bundle_hash"], "archival_bundle_after_backfill_hash": reconstructed_after["bundle_hash"],
                "warning": "A source-available reconstruction can use verified archive material not ingested by the historical engine. It cannot prove actual live detection at that time; a changed evidence manifest makes a new bundle."},
            "delivery_transitions": transitions, "denied_state_gates": denied_state_gates, "kind_state_gates": kind_state_gates,
            "policy_counterexample": {"original_policy_score": score_bundle(old_bundle, mk), "alternate_policy_score": score_bundle(alternate_policy_bundle, mk),
                                     "alternate_policy_bundle_hash": alternate_policy_bundle["bundle_hash"]},
            "collision_quarantine": collision_notes, "onchain_semantics": sem,
            "bundles": {"frozen_actual_at_cutoff": old_bundle, "source_available_at_cutoff": reconstructed_after,
                        "alternate_policy_at_cutoff": alternate_policy_bundle},
            "records": [record.payload() for record in records]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write exact deterministic JSON result; default stdout")
    args = parser.parse_args()
    rendered = json.dumps(run(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
        report = json.loads(rendered)
        print(f"PASS {report['summary']['passed']}/{report['summary']['total']} synthetic checks; external sends=0; output={args.output}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
