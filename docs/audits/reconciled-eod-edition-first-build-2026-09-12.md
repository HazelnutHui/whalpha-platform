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

## Contract 1.2 build and price-collision wiring stop

The first clean 1.2 implementation revision was
`89a4f1bfc14ad71d89769c614a133341b688cd7f`. It completed 26 batches and
retained 39 successful sessions from batch 27 before stopping on 2025-11-18.
The incomplete candidate contains 1,079 completed partitions, no interval
marker, and made zero external requests or `/data` writes.

The failed later-reacquisition session reproduced all 9,041 base records with
zero economic change or absence and added three records. `BCPC` and `TPC` were
already recognized as expected additions. `SRVR` was initially unrecognized:
the price package contains both `SRVR` and `SRVr`, same-session Identity
resolves only exact `SRVR` as an ETF to the existing stable ID, and legacy
normalized mapping omitted that valid bar.

ADR 0203 defines the repair in terms of an exact Grouped Daily symbol
collision plus exact Identity resolution. The edition builder incorrectly fed
its expected-addition classifier from Identity's collision set rather than the
price package's collision set, despite the correct price-collision classifier
already existing. The wiring now derives collision groups from the exact price
payload and uses Identity only to resolve an already-canonical stable ID. It
does not mint an instrument or infer eligibility from ticker form.

A dedicated fixture with price-only `SRVR`/`SRVr` collision passed. A real
network-disabled replay then classified all three additions as expected, all
9,041 base rows as later-source provenance-only changes, and zero unexpected,
absent, or economic changes. The complete 2,522-test API suite passed with only
the same two pre-existing dependency deprecation warnings.

## Completed contract 1.2 successor

The clean successor was built from implementation revision
`c798e582b0ad3b49ada5fc7fde94125382ef9c06` with fixed creation time
`2026-09-12T05:04:00Z`. It reused none of the stopped candidates. All 31
batches completed and the final interval marker passed formal reread:

- edition ID: `reconciled-eod-v12-20210913-20260812-c798e58`;
- 1,234 sessions / 10,376,263 records;
- 947 retained-original / 287 later-reacquisition sessions;
- 2,461 accepted additions / 50 source-proven expected absences /
  2,648,128 source-proven provenance-only ticker-case repairs;
- interval fingerprint:
  `098ff756a463c0bf142d9ce597375e3a0574db02ca641fcdcef9b6e72cb6b5e3`;
- owner-only custody: 2,469 files / 1,083,699,732 bytes, zero symlinks and
  zero staging or temporary residue; and
- zero external requests and zero canonical `/data` writes.

The separately generated no-write Apply plan formally reread the candidate and
bound every artifact plus canonical pre-state fingerprint
`a83136b65d76371a9932aa58fc142aa815d1303dc89f600d852cc177eea36d5e`.
Its file SHA-256 is
`7e9c13b957ad9e2fceb850e9da645356c2e1930800d943f2af3927da31115505`
and logical fingerprint is
`6a09ef14c77c475d46f0ae1d20f89058ea1457e32a1e633179b642edccbcf1d5`.
It was emitted as `ready_for_separate_apply` with all authority flags false.

## Canonical Apply and postflight

The exact plan values were explicitly approved. Atomic Apply published all
2,469 files / 1,083,699,732 bytes without reusing a prior target and formally
reread all 1,234 sessions / 10,376,263 records. The reported interval
fingerprint matched the candidate and plan. External requests, overwritten
partitions, deleted partitions, Production authority, and research-performance
authority remained zero or false.

Independent postflight found exactly 1,235 directories at mode 0755, all 2,469
files at mode 0644, zero symlinks, and zero staging residue. The project context
report remained network-disabled and confirmed:

- 18,172 canonical files / 7,019,486,412 bytes;
- canonical inventory fingerprint
  `8baec95b3a4e81cc2b4ca05f9f1fb24a8a112237c6c217bf88c09066462aa307`;
- existing EOD and Identity aligned through 2026-09-11; and
- Production release and current-session freshness unchanged.

## Next action and authority

Construct the separately versioned final Historical Coverage and research-input
admission evidence. No action recorded here changes canonical EOD V1,
Historical Coverage, research admission, performance claims, Candidate,
Production, publication, deployment, or the website.
