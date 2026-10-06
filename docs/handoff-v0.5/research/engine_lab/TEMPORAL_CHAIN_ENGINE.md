# Temporal and on-chain engine lab

Reviewed and run on 2026-10-02. The deterministic offline experiment passes **29/29 synthetic checks**. It demonstrates failures caused by current-row historical queries, arrival-order updates and stale delivery dependencies, with guarded counterexamples that preserve dated revisions and frozen snapshots. It makes **zero external sends** and uses no RPC, provider account or live market data. These results establish behavior on constructed cases, not production consensus verification, historical prediction or financial accuracy.

The owner selected BIST, Turkish investment funds, crypto and US equities with meaningful on-chain experience (DEC-019; `research/USER_DECISIONS_2026-10-02.md:8`). EVM and Solana remain proposed adapter paths; exact networks and providers need capability and rights evidence (DEC-015). This lab does not reduce that target or count either adapter as implemented.

## Authority and requirement coverage

The working package is an implementation specification and offline harness, not a deployed application (`AGENTS.md:3`). This research follows `AGENTS.md:19–24,31,37`, document 13's revision/correction and replay requirements (`docs/13_Decision_Confidence_and_Validation.md:42–50,59–67`), and document 15's separate clocks, immutable records, replay bundles and send-time revision checks (`docs/15_Domain_Model_and_Persistence.md:7–9,36–40,51–54,69`).

| Requirement | What the lab supports | Completion boundary |
|---|---|---|
| FR-018, FR-019 | Explicit UTC source-availability and ingestion timestamps | No production normalization/freshness adapter |
| FR-041, FR-042 | EVM reorg and Solana commitment policy counterexamples | Neither proposed adapter is implemented or validated |
| FR-043, FR-044 | Raw transfer and account-authority semantics; immutable dependency inputs | No actual transaction parsing, address attribution or combined live event |
| FR-108, FR-109; NFR-037, NFR-038 | Frozen synthetic replay with known-cutoff revision selection | No rights-cleared historical dataset; historical-proof requirements remain open |
| NFR-004, NFR-036 | Exact-duplicate/reorder invariance and stored threshold counterexample | No durable database or concurrent ingestion test |
| FR-089; document 13 §5 | Local suppression/correction transitions when evidence changes | No email, consent store, outbox, leases or delivery completion |

## Experiment and reproducibility

The four owned artifacts are this report, `experiments/temporal_chain.py`, `research/engine_lab/temporal_chain_results.json` and `research/engine_lab/temporal_chain_sources.json`. The Python file uses only the standard library. From the package root:

```sh
python experiments/temporal_chain.py --output research/engine_lab/temporal_chain_results.json
```

Observed output:

```text
PASS 29/29 synthetic checks; external sends=0; output=research/engine_lab/temporal_chain_results.json
```

Two additional stdout executions were compared byte for byte with each other and with the saved results; all three outputs matched. The input contains 14 records, including an exact duplicate, with 13 unique `(key, revision)` pairs. Seed 50000 fixes 100 permutations. At cutoff `2026-10-01T10:03:00Z`, the actually-ingested snapshot has four selected records and the source-available reconstruction has six.

| Artifact | SHA-256 after the verified run |
|---|---|
| Python experiment | `90691c5b9b1878362db8f9d4655e6dd6e612525e37ddfdfa5a29ad7279d216c5` |
| Saved results | `f108171ab58352459eb10b365cb0339156a0f42b1af645db5cd0628e3a5d53e4` |
| Ordered synthetic inputs | `88ee654dffe16176be21d1fdee931bff9d0443499215c6c9a2edf385eceefba5` |

## Time, revisions and knowledge

Bitemporal systems separate application-valid time from system history. MariaDB's official [bitemporal](https://mariadb.com/docs/server/reference/sql-structure/temporal-tables/bitemporal-tables) and [system-versioned](https://mariadb.com/docs/server/reference/sql-structure/temporal-tables/system-versioned-tables) documentation provides a concrete conceptual reference, including historical state queries. This is background methodology; no MariaDB dependency or SQL was introduced. For this product, source publication and availability add knowledge constraints that a database update timestamp alone cannot supply.

| Clock or version fact | Question it answers | Lab rule |
|---|---|---|
| `effective_at` | When did the measured event occur, or when does an announced action take effect? | Future market/chain observations excluded; a published future-effective notice can remain an upcoming-event document |
| `published_at` | When was this version published? | Publication later than cutoff excluded |
| `available_at` + provenance | When was this version obtainable according to the stated evidence? | Must be at/before cutoff and OBSERVED or ARCHIVE_VERIFIED; UNKNOWN excluded |
| `ingested_at` | When did this engine ingest this version? | Must also be at/before cutoff for ACTUALLY_INGESTED |
| Source key + revision + payload hash | Which version is being used? | Latest eligible revision selected; exact duplicates collapse; conflicting same-identity payloads quarantine the key |
| Block/slot, canonicality or commitment version | When was the chain-state conclusion known? | Later ORPHANED/FINALIZED versions cannot enter an earlier snapshot |

`SOURCE_AVAILABLE_RECONSTRUCTION` asks what a reconstruction could use under verified historical availability assumptions. `ACTUALLY_INGESTED` asks what this engine had ingested. They answer different questions. A late archive can legitimately enrich a new reconstruction bundle without proving the live engine detected an event at that earlier time. The archive-verification labels here are fixture assumptions; no historical archive was verified.

The snapshot model assumes source revision numbers are correctly identified and monotonically ordered. A real provider may require explicit supersession relationships instead. Payload timestamps are immutable source-record facts in the fixture; a repeated transport receipt must have separate receipt metadata rather than changing the original payload identity. This lab has no historical universe membership, corporate-action history, point-in-time rights registry or source-signature verification. Its bundles do not include an executable/dependency manifest; the report records the actual script hash separately. Production reproducibility needs those additional bindings. Toy RVOL scoring uses fixed valid fixtures and is not a general numeric-input validator or empirically selected detector.

## Observed temporal counterexamples

| Constructed case | Naive result | Guarded result and actual evidence |
|---|---|---|
| A volume bar is revised after the 10:03 cutoff | Current row uses revision 2: ratio 1.2, NOT_FLAGGED | Historical snapshot retains revision 1: ratio 6, CANDIDATE at threshold 3 (C01–C02) |
| Old exact duplicate arrives after revision 2 | Last-arrival processing restores revision 1 and CANDIDATE | Current eligible revision stays 2, ratio 1.2 (C03) |
| Notice available 10:02, ingested 10:07 | Treating publication as ingestion could invent a live detection | Present in source-available reconstruction, absent from actually-ingested cutoff (C04) |
| Archival bar available 09:31, ingested 10:08 | Historical availability could be assumed from event date | Included only in the explicitly reconstructed basis under fixture ARCHIVE_VERIFIED provenance (C05) |
| Historical availability unknown | Backfill could be relabeled contemporaneous | Excluded (C06) |
| Late material is appended after a bundle is frozen | Querying current data can silently change an old result | Actual-ingestion bundle hash unchanged; additional archive evidence creates a distinct reconstruction bundle (C07–C08) |
| Conflicting content has the same key and revision | Last-write-wins arbitrarily picks an answer | Entire conflicting source key quarantined (C10) |
| Same evidence is frozen under threshold 7 | Merely hashing config could leave global threshold 3 in use | Stored bundle config drives scoring: ratio 6 becomes NOT_FLAGGED at 7 (C22–C23) |

In 100 seeded permutations, the guarded current snapshot produced the same hash 100 times; last-arrival processing selected the stale market revision in 65 permutations. These are exact results for one toy input set, not statistical performance estimates or production delivery failure rates.

The actually-ingested cutoff bundle hash remains `f367c3a49a005325c0a804c685544c23134545a9cb8cfe445f20d7cc7e260875` after late records are appended. The reconstructed bundle changes from `707b475dfd70aaa4ef2d6d1d5b43263ed8127c7dc1158ca2c6dc11b6db546d9c` to `f03767f5645f0a162572d4505063876e6c4b50d7efc7608abfaae1de3a738870` when its evidence manifest expands. Changing serialized content without changing its saved hash is detected (C09). A checksum is an integrity comparison, not proof that the source or archive is authentic; an attacker able to replace both content and hash is outside this experiment.

## Chain state and delivery dependencies

Ethereum's official [JSON-RPC documentation](https://ethereum.org/developers/docs/apis/json-rpc/) distinguishes block-selection tags including latest, safe and finalized, and reports removed logs when a reorganization removes them. Ethereum's [proof-of-stake documentation](https://ethereum.org/developers/docs/consensus-mechanisms/pos/) explains checkpoint finality under stake-voting assumptions, the economic cost of reverting finalized history and circumstances in which finality stalls. These are Ethereum-specific semantics; generic EVM compatibility does not prove identical finality on another network.

Solana's official [RPC overview](https://solana.com/docs/rpc) distinguishes processed, confirmed and finalized commitments: processed observations may roll back, confirmed has supermajority direct votes and finalized has the strongest lockout. Its [terminology](https://solana.com/docs/references/terminology) ties rooted history and finality to consensus. Persist commitment and the observation context; do not silently promote a processed or confirmed result to finalized. The same RPC overview warns that shared public endpoints can rate-limit or block clients and are unsuitable as a production capacity plan. Documentation of a method is not evidence of archival coverage, provider uptime or licensed entitlement.

| Synthetic chain case | Local outcome | Boundary |
|---|---|---|
| EVM block A is provisional at 10:02, then removed at 10:04 | Intent bound to old revision becomes SUPPRESSED | Reorg is a fixture input; no header ancestry or consensus verification occurs |
| An artificial earlier SIMULATED_ACCEPTED intent loses evidence | CORRECTION_REQUIRED | This is an injected past state to test correction policy; finalized-only policy would have blocked the original provisional intent |
| Solana observation is CONFIRMED at 10:03 | SUPPRESSED under finalized-only local policy | Future FINALIZED revision at 10:05 is excluded from the earlier cutoff (C13, C28) |
| Fresh intent binds the finalized EVM or Solana revision | SIMULATED_ACCEPTED, LOCAL_DRY_RUN, external_send=false | Acceptance only within this offline model; neither consensus nor external delivery is proven |
| Binding hash/revision differs from current evidence | SUPPRESSED | No stale approval reuse (C15–C16) |
| Identical current/dependency payload is RETRACTED, INVALIDATED, UNKNOWN or ORPHANED, with finality gate off | Each independently rejected as STATE_NOT_ADMITTED | State whitelist is checked in addition to exact binding (C24–C27) |
| MARKET has FINALIZED state, or CHAIN has ACTIVE state | Both rejected | The admitted state set is kind-specific (C29) |

The gate is a small policy function, not an outbox. It lacks atomic enqueue/send transactions, durable cancellation races, event/evidence dependency graphs, approval revocation history, recipient consent, retry/idempotency semantics and provider acceptance reconciliation. When finality evidence changes, the old bound intent is canceled; a newly reviewed revision must create a fresh binding. No timeless mutation of the old intent is demonstrated.

## Transfer and ownership semantics

[ERC-20](https://eips.ethereum.org/EIPS/eip-20) specifies transfer-event sender, recipient and raw value, while token decimals are optional. Inference: those fields do not establish a purchase price, consideration, a sale or an economic beneficial owner. The fixture preserves raw amount `500000000`, with decimals, human amount and monetary notional unknown. A transfer could be custody movement, a deposit or settlement of a separately verified trade; none is asserted as the explanation. Missing decimals are not defaulted to 18 (C18, C21).

Solana's [token-account documentation](https://solana.com/docs/tokens/basics/create-token-account), [token model](https://solana.com/docs/tokens) and [transfer documentation](https://solana.com/docs/tokens/basics/transfer-tokens) distinguish account addresses, token-program ownership, token authority, mint authority and delegates. [SetAuthority](https://solana.com/docs/tokens/basics/set-authority) can change particular authority roles, so current authority is not automatically historical authority. [Token Program multisig documentation](https://www.solana-program.com/docs/token) permits multisig authorities, and the [official pinned state definitions](https://github.com/solana-program/token/blob/6d18ff73b1dd30703a30b1ca941cb0f1d18c2b2a/program/src/state.rs) separately encode account owner/delegate, mint authority/freeze authority and multisig signer structure. These capabilities describe permissions, not human identity.

| Term | Observable meaning | Unjustified inference |
|---|---|---|
| Token account address | Storage account for a mint balance | One account is one investor |
| Account program owner | Program authorized to manage the account's data | Token Program owns all tokens economically |
| Token authority / parsed token `owner` | Authority for allowed token operations, with delegation/other mechanisms possible | One authority is one independent person |
| Mint authority / freeze authority | Separate supply/freeze permissions | Either identifies every holder or proves a scam |
| Verified, dated exchange label | Attribution under a separately reviewed source | Every transfer into it is a sale |
| Beneficial owner | Economic ownership requiring additional evidence | Resolved from a raw address or token account |

The complete **toy** mint snapshot contains four token accounts, with two sharing authority W1. Direct authority aggregation is 700/200/100 across three authority addresses; the number of beneficial owners is unknown. Account count four is not owner count four (C19). This proves the account/authority distinction on the fixture, not completeness or ownership of any real mint. The official [getTokenLargestAccounts](https://solana.com/docs/rpc/http/gettokenlargestaccounts) method returns only the 20 largest accounts, so a response is not a complete holder universe. [getTokenAccountsByOwner](https://solana.com/docs/rpc/http/gettokenaccountsbyowner) supplies a context slot and owner query parameters; a queried address is not a census of beneficial owners, and `minContextSlot` is not an exact historical snapshot selector.

## Hypotheses and implementation decisions

| Status | Hypothesis or design | Evidence and disposition |
|---|---|---|
| KEEP | Immutable source versions plus explicit cutoff and replay basis | C01–C08; actually-ingested and source-available reconstructions stay separate |
| KEEP | Evidence/config manifests control reproducible scoring | C07–C09, C22–C23; threshold in frozen content actually drives toy RVOL outcome |
| KEEP | Deduplicate exact identities; quarantine conflicting identities | C03, C10, C17; no arrival-order overwrite |
| KEEP | Persist chain context and dated canonicality/commitment conclusions | Official Ethereum/Solana semantics; C11–C14, C28; later finalization cannot enter earlier features |
| KEEP | Check binding and admitted states immediately before local acceptance | C15–C16, C24–C29; stale or invalid evidence fails closed |
| KEEP | Display raw transfers and authority facts with bounded interpretation | C18–C21; evidence can be meaningful without inventing sale/people labels |
| REJECT | Use the latest row to recreate historical knowledge | Constructed earlier CANDIDATE becomes NOT_FLAGGED using later correction |
| REJECT | Receipt order decides current revision | 65/100 permutations restore an older revision |
| REJECT | Confirmed means finalized, or all EVM chains share Ethereum finality | Official commitment/network distinctions; C13, C28 |
| REJECT | Token transfer implies sale; account/address count implies people | Protocol records lack the required economic attribution |
| REJECT | Missing precision or unavailable RPC data means zero/default/absence | Preserve missingness; require explicit coverage before absence claims |
| DEFER | Exact networks, adapter schemas, provider history/finality capability and rights | EVM+Solana proposal needs real read-only provider spikes after selection; no RPC performed here |
| DEFER | Actual canonical ancestry, transaction decoding, native ETH/SOL, Token-2022 extensions, Layer 2 finality, bridges and BTC | None is implemented by string-state fixtures |
| DEFER | Beneficial-owner clustering, exchange labels and historic ownership | Require validated dated evidence and uncertainty; never substitute raw accounts |
| DEFER | Complete concentration/supply metrics and fiat transfer notional | Need full context-aligned coverage, supply definition, token precision and authorized contemporaneous quote evidence |
| DEFER | Production database, replay registry, auth, durable outbox, concurrent corrections and bundle authenticity | Lab checks cannot establish these production properties |

## Useful next boundary

A bounded on-chain slice can expose a finalized transfer fact with exact network, contract/mint, transaction/instruction locator, raw unit, source context, availability time and interpretation limits, then correlate it with eligible market evidence. It can expose concentration by verified direct authority if coverage and denominator are established. It must reserve exchange-flow, sale, cluster and beneficial-owner labels for separately verified evidence. A source-backed implementation of that slice can be meaningful; this synthetic lab by itself does not satisfy the owner's actual on-chain demonstration acceptance.

Next, record the actual supported network/asset/provider combination and perform a bounded, authorized capability spike to establish historical access, finality/commitment behavior, reorg handling, pagination/gap detection, token precision and rights. Then replay independently dated real examples through durable revisions and exact dependency invalidation. Existing budget/account/release gates remain separate; this research caused no migrations, service provisioning, spend, real-data publication or remote action.

## Source-review depth

`temporal_chain_sources.json` records all 15 primary sources, checked date, URLs, retrieval references and exact sections reviewed. Documentation was read at selected relevant sections, not comprehensively audited. The pinned Token Program state file was inspected for Mint, Account and Multisig definitions without compiling it. MariaDB was conceptual background only. No downloaded chain payloads, SDK execution, network-consensus experiment or provider capability test occurred.
