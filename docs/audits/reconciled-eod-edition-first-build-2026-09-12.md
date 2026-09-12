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

## Next action and authority

Run a new candidate from an empty owner-only root, a new edition ID, one clean
1.1 implementation revision, and one fixed creation time. The stopped 1.0
candidate is not reused.

No action in this audit changes canonical EOD V1, Historical Coverage,
research admission, performance claims, Candidate, Production, publication,
deployment, or the website.
