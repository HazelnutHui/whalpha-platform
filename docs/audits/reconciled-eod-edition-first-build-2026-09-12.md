# Reconciled EOD Edition First Real Build Audit — 2026-09-12

## Boundary

Build the first immutable corrected EOD price-family candidate for ADR 0207's
exact 1,234-session interval from 2021-09-13 through 2026-08-12. Construction
ran on Dell with four worker processes, no network access, no canonical
`/data` write, and no research or Production authority.

The sealed Source Coverage artifact is
`coverage-2021-09-13--2026-08-12-20260912T023152Z.json`:

- file SHA-256:
  `4dc34a7851a0a2d851d4d75da86cd66a2c6a34508a9f016b08fa5a42d2d34ba9`;
- logical fingerprint:
  `9bd386efe1fed7e6c39c5f11bc85dfe82f5f71d039079761ba838fe952e2ac6a`;
- status: `ready_for_candidate_build`;
- 1,234 target sessions, 947 retained-original sources, 287 visibly
  later-reacquired sources, and zero missing, invalid, or conflict sessions.

## Contract 1.0 pilot and stop

The clean implementation revision was
`833272770cf32a134b78e83e1e7a1e39c37d16e1`. The first 40-session pilot
published 304,779 records in 94 seconds, used about 3.7 CPU cores on average,
peaked near 360 MiB RSS, and produced zero failures or diffs.

The resumable controller then reused those 40 sessions and completed five more
40-session batches. Batch seven covered 2022-08-25 through 2022-10-20 and
stopped with five failed sessions after retaining 35 additional successes.
The incomplete 1.0 candidate contains 275 completed session partitions and no
interval manifest. It is retained as non-authoritative execution evidence and
must not be mixed with the successor contract.

Failed sessions were 2022-10-10, 2022-10-12, 2022-10-13, 2022-10-14, and
2022-10-18. Each contained zero economic changes, four or five expected
case-sensitive additions, and one absent EOD V1 key.

## Root cause and 1.1 response

All five absences were the same stable-identity case. The exact retained price
symbol was `ALpA`, while legacy EOD V1 had normalized its source ID to `ALPA`
and bound the bar to the common-stock instrument. Exact same-session Identity
source classifies `ALpA` as an excluded preferred stock and `ALPA` as a
different common stock. The exact mapper therefore correctly removes the
false common-stock bar.

ADR 0208 and manifest contract 1.1 now distinguish source-proven expected
absences from unexpected absences. The exception requires retained-original
price custody, exact case-collision and exclusion evidence, stable-ID binding,
source row/timestamp and observation-time equivalence, OHLCV equivalence, and
neutral adjustment factors. Later-reacquired sources and every unproven
absence remain quarantined.

The contract, pure diff, persistent session/interval binding, batch/build
accounting, and Apply-plan accounting have focused automated coverage. A
temporary real-data candidate then published and formally reread all five
sessions under session manifest 1.1: 40,812 records, 21 accepted additions,
five expected absences, zero unexpected absences, zero economic changes, and
no failed session. It made zero external requests and zero `/data` writes; its
temporary directory was automatically removed after validation.

## Contract 1.1 build and second typed stop

The clean 1.1 implementation revision was
`b261990d9bfbe76c2dbde97d66c85d4d79ff28d9`. Its first seven batches completed
280 sessions, including the five dates that stopped contract 1.0. Batch eight
retained another 20 successful partitions and stopped on 20 dates from
2022-10-27 through 2022-12-16. The incomplete 1.1 candidate therefore contains
300 completed sessions and no interval marker. It made no external request and
no `/data` write.

The 20 failed candidates contained 86 accepted additions, five ADR 0208
expected absences, zero unexpected additions or absences, and zero economic
changes. Their only blocker was 30 retained-source provenance-only changes.
Field-level review showed that every change only restored exact provider ticker
case inside `source_record_id`: examples include `RXOW` to `RXOw`, `FGW` to
`FGw`, and `BAMW` to `BAMw`. Stable instrument, source timestamp, observation
time, OHLCV and adjustment values, revision state, quality state and flags, and
schema version were unchanged.

Same-session Identity source resolves every exact mixed-case ticker to the same
stable ID, contains no exact entry for the legacy upper-case spelling, and the
canonical normalized Resolver reproduces the old binding. ADR 0209 and
contract 1.2 therefore admit only this eight-condition source-proven repair and
retain separate expected/unexpected provenance accounting. A network-disabled
four-worker real-data replay of all 20 failed dates returned 20 accepted
case-sensitive reconciliations, 86 additions, five expected absences, 30
expected provenance-only changes, and zero blocking or economic changes.
Fifty-seven focused tests and the complete 2,521-test API suite passed under
contract 1.2; the only additional output was two pre-existing dependency
deprecation warnings.

## Next action and authority

Run a new candidate from an empty owner-only root, a new edition ID, one clean
1.2 implementation revision, and one fixed creation time. Neither stopped
candidate is reused.

No action in this audit changes canonical EOD V1, Historical Coverage,
research admission, performance claims, Candidate, Production, publication,
deployment, or the website.
