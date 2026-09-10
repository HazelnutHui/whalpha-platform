# Five-Year Research Membership Custody Audit — 2026-09-10

## Scope

This audit records the first durable ADR 0197 archive of latest-vintage
reconstructed historical Universe Membership. It contains no strategy trigger,
outcome, return, parameter selection, Candidate activation, web publication,
or Production action.

## Input and preflight

- Candidate root: `/tmp/whalpha-canonical-membership-full-shadow-af415a4`
- Candidate partitions: 300 unique completed sessions
- Candidate interval: 2025-06-23 through 2026-09-03
- Methodology: `provider-form-complete-base-point-in-time-v3`
- Preflight: 300 plan-required, zero duplicate business keys, zero existing
  target conflicts, zero external requests, zero canonical writes

The candidate was generated from same-session normalized Identity sources and
canonical EOD input but retrieved/evaluated after the represented sessions. It
therefore remains `reconstructed_point_in_time_latest_vintage` and
`not_as_operated`.

## Apply result

- Research partitions applied: 300
- Membership decisions: 5,571,154
- Failed partitions: 0
- Reused partitions: 0
- Overwritten partitions: 0
- Deleted partitions: 0
- External requests: 0
- Signal/development/validation/holdout/performance/Candidate/Production/web
  authority: all false

Each target contains the original `manifest.json`, original
`part-00000.parquet`, and a `research-custody.json` marker written last inside
an atomic directory publication. Every Apply reread and validated the full
Parquet rows. The persistent per-session plan binds exact source and target
paths, physical hashes, logical fingerprint, source fingerprints, source
cutoff, evaluation time, represented session close, record count, and
evaluated-base count.

The research family is physically distinct from the three existing
signal-eligible Membership partitions. No file was added below the
signal-eligible Membership or publication-marker roots.

## Postflight census

The network-disabled five-year census completed with fingerprint
`c193895b7cb795fb5054c5e8493bb7c5e438e646c37e03d336a82d52f3a903e7`.
Membership now reports 303/1,255 covered sessions: 300 reconstructed research
sessions plus three signal-eligible prospective sessions. The combined record
count is 5,631,046, including 174,282 quarantined decisions. Evidence tier is
`mixed`; `reconstructed_membership_not_signal_eligible` and physical
separation remain explicit reason codes. Foundation state remains
`quarantined` and performance claims remain unauthorized.

## Concurrent-writer safety event

The separate EOD/Identity backfill completed its first 20-session checkpoint,
then continued until its whole-data compare-and-swap guard observed this
research-family write between planning and Apply. It stopped with
`SameDayCatchupError` as designed. No target was overwritten and no staging
residue exists.

At postflight, EOD had 346 sessions from 2025-04-24 through 2026-09-09;
Identity had 347 partitions from 2025-04-23, leaving exactly 2025-04-23 as an
Identity-only continuation point. Normalized Identity source custody had 345
partitions. The retained 2025-04-23 package is reusable. Further canonical
writers must run serially until whole-root Apply state is scoped more narrowly.

The full read-only inventory at 2026-09-10T09:38:58Z was 5,660 files,
2,603,087,394 bytes, zero symlinks, zero publication residue, fingerprint
`641fa52e8936956456f9259afc32cfd419e0b1d15238e44fb3fb6952e0600dc6`.

## Stage decision

ADR 0197 custody mechanics and the first 300-session archive pass. No further
micro-optimization is authorized by this result. The next independent action
is to resume the exact EOD/Identity backfill with no concurrent `/data` writer,
then extend research Membership only from formally completed inputs. Lifecycle,
actions, terminal outcomes, adjustments, admission, and performance remain
separate later gates.
