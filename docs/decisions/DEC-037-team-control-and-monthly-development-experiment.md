# DEC-037 — Team control and a separate monthly development experiment

Mirza, 2026-10-11, during the final product continuation before 12:30 Istanbul.

- Add admin Stop/Resume for the autonomous local team. Pause is persistent, audited and global across analysis
  views; it blocks new scans, claims and agent model calls, while admitted paid work finishes. Resume preserves
  queues, prior messages, original decisions and human authority. Interactive chat is not a background queue worker.
- Make `/results` canonical; retain `/sonuclar` as a permanent, query-preserving redirect. Add Review to the navbar
  for analysts/admins and clearly distinguish real team proposals, absent/invalid proposals and rule-only results.
- Repair the fund layout and source cards using the already eligible KAP data. THF/TP2 each have 11 monthly periods,
  AAL has 12; no invented investor counts or October TEFAS snapshots may fill September's missing information.
- Mirza chose **also attempt a separate development experiment**. Its fixed factor-two/half monthly paired rule
  was committed in `100ddfb` before the first real calculation. The new protocol is
  `research/events/2026-09-17-spk-liquidations/kap_monthly_scale_v1/PROTOCOL.md`; it is now immutable.
- The existing frozen detector results remain unchanged. This experiment and the later-label comparison are
  separate from stored detector runs, evidence packets and agent inputs. No threshold fitting to the SPK list.
- Development outcome: 101 of 2,133 funds assessable; three monthly flags, two later on the SPK list. KHA is additional
  to the price baseline: the separate union is 24/131 instead of 23/131, and five/eight case funds instead of four/eight.
  Limited coverage, related inputs, prior case inspection and no held-out set prevent a validated performance claim.

The user's new experiment authorization permits adding this previously nonexistent protocol. Protected-path checks
must verify its added status and its exact `100ddfb` bytes; they still block every modification/deletion of existing
protocols, frozen detectors, registered sources, the handoff manifest and `raw/`. No squash or force push.
