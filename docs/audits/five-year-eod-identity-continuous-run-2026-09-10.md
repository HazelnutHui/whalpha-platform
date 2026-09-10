# Five-Year EOD and Identity Continuous Run — 2026-09-10

## Scope

The finite Dell run targets exactly 1,255 XNYS sessions from 2021-09-09
through 2026-09-09.  It uses a 0.25-second serial provider interval, batches of
20 sessions, a 24-hour runtime ceiling, 2 GiB memory ceiling, no process
restart, immutable per-session packages, exact Apply plans, locked whole-root
CAS, and formal post-Apply reread.

## One recovered consistency stop

The first unit correctly stopped after a separate research Membership Apply
changed the whole `/data` inventory.  Identity for 2025-04-23 had already
completed, while its EOD target remained absent.  The retained EOD plan bound
inventory fingerprint
`fd66f3bb2408c416b462cf95c14b9372abb386985f80d963aea8886e243550b3`;
the post-Membership inventory was
`641fa52e8936956456f9259afc32cfd419e0b1d15238e44fb3fb6952e0600dc6`.

The stale plan and artifacts were not deleted.  They were moved within the
exact owner-only session workspace to
`failed-eod-canonical-apply-plan-attempt-1.json` and
`failed-eod-canonical-apply-plan-attempt-1.artifacts`.  A new plan was built
against current inventory.  It reused the formally validated EOD package,
made zero provider requests, applied and reread 8,584 rows, and advanced the
continuous left boundary to 2025-04-23.

## Resumed execution

The unique continuation unit
`whalpha-five-year-backfill-20260910c.service` began at 2026-09-10 09:56:09
UTC from clean source revision
`d9d77c124f1b9300613d97923493a1e696e1262c`.  Its first checkpoint completed
20 adjacent sessions through 2025-03-25 with 260 provider requests, zero
transient retries, and no analytics, publication, deployment, or Production
action.

At 2026-09-10 10:30:47 UTC, a direct partition census observed 386 contiguous
EOD sessions through 2025-02-26 and 387 Identity partitions through
2025-02-25.  The one-partition Identity lead is the expected safe ordering
inside the current session transaction, not a completeness claim.  The unit
remained active, used about one CPU core, and had not reported a transient
retry or source failure.

This audit remains the execution record until the finite run completes or
stops at another explicit resumable boundary.  Volatile progress is not a
completeness claim.

## Bounded historical alias stop

The continuation completed three more 20-session checkpoints through
2025-01-27, then completed 2025-01-24 and 2025-01-23 inside the next batch. It
stopped before publishing 2025-01-22 Identity. At the stop, EOD and Identity
were aligned at 409 sessions with 2025-01-23 as the common left boundary. The
2025-01-22 Identity acquisition package was complete and immutable; no plan,
canonical Identity, or EOD package for that date existed.

An offline reread reproduced the only failing gate. The package contains
11,166 raw rows, 9,356 eligible observations, 8,467 resolved observations, 831
unresolved observations, and 58 stable-identifier collision observations in
29 two-ticker groups. Collision ratio is 0.6199%; eligible identity coverage
after preserving all conflicts in the denominator is 90.4981%. Adjacent
2025-01-23 and 2025-01-24 packages each contained zero collision observations.

Every conflict remains ambiguous and absent from canonical Instrument and
Resolver output. ADR 0201 permits this bounded later-vintage reconstruction
under a 1.0% ceiling while leaving the prospective 0.1% gate unchanged. This
does not resolve ticker history or upgrade the reconstructed family to
`as_operated` evidence.

## Fail-closed VWAP precision stop

The successor `whalpha-five-year-backfill-20260910d.service` continued from
the alias gate and stopped at 2026-09-10 20:51:39 UTC after 9 hours 32 minutes.
A 21:03:41 UTC network-free quiescent report found 942 contiguous EOD sessions
from 2022-12-06 through 2026-09-09 and 943 Identity partitions from 2022-12-05
through 2026-09-09. Identity source custody has 941 partitions; 2026-08-13 and
2026-08-19 remain source-unbound. The exact inventory is 12,216 files and
4,732,957,086 bytes with fingerprint
`f89a02ad0625b8391dc46e383e8056567c64c94b682e29ab0395f63008501559`,
zero symlinks, and zero publication residue.

The 2022-12-05 Identity transaction completed. EOD plan construction then
rejected a provider VWAP whose decimal scale exceeds the canonical limit of
10. The typed persistence exception prevented silent rounding and no
2022-12-05 EOD partition was published. The retained one-partition Identity
lead is the exact safe restart boundary. The failed unit remains stopped; its
precision policy requires an explicit decision and regression fixture before
one unique continuation is started.

## VWAP precision resolution

Offline inspection of the retained 2022-12-05 Grouped Daily package found
11,084 source rows and exactly 314 non-null VWAP values above canonical scale
10. Their scales range from 16 through 20. Quantizing them with the ADR 0202
round-half-even rule changes no value by more than `1E-16`; OHLC and volume
have zero precision/scale violations in the same package.

A zero-write replay against the formally read same-day Identity produced 8,156
canonical candidate rows, counted all 314 normalizations, and passed every EOD
quality gate. Focused provider/persistence regression passed 87 tests; the
complete API suite passed 2,413 tests. The provider-neutral repository still
rejects over-scale VWAP, proving that normalization is confined to the Massive
mapping boundary. No canonical data was written during diagnosis or testing.

## Recovery and resumed continuation

After clean source commit `1f56f3ff7d0bb5319e40ae817ac75241391bfe7b`, one
foreground recovery session reused both 2022-12-05 canonical Identity and its
immutable EOD package. It made zero external requests, published and formally
reread 8,156 EOD rows, and aligned EOD/Identity at 943 sessions with
2022-12-05 as the common left edge.

The exact empty plan-artifact directory left by the failed builder contained
no file or symlink and was removed with non-recursive empty-directory checks.
The unique user unit `whalpha-five-year-backfill-20260910e.service` then
started with the frozen 1,255-session interval, 20-session batches, serial
0.25-second request spacing, a 24-hour runtime limit, and a 2 GiB memory limit.
At 21:36:11 UTC it was active, and 2022-12-02 Identity and EOD had both
completed, establishing an at-least-944-session aligned live checkpoint.
