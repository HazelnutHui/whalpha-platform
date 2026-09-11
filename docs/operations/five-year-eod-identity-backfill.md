# Five-Year EOD and Identity Backfill

> **Current disposition:** the fixed 2021-09-09 through 2026-09-09 run is
> terminal historical evidence and must not be restarted. Under ADR 0206,
> normal daily updates will roll the source target to an interval beginning
> 2021-09-13. The first 20 available sessions become disclosed feature warm-up;
> the reserved external warm-up workspace is not populated under Starter.
> Commands below document the completed fixed-interval procedure, not the next
> operator action.

## Purpose

This runbook implements the first acquisition stage of ADR 0196. It extends
the canonical Dell EOD and same-session point-in-time Identity families across
one frozen XNYS interval. It does not construct historical Membership,
Lifecycle, Corporate Actions, Adjustments, Fundamentals, Classification, or
final Historical Coverage.

The authoritative first interval is 2021-09-09 through 2026-09-09, exactly
1,255 XNYS sessions. Both endpoints are passed to the executor. A session-count
shortcut must not be used for this run because a later daily append would move
the left boundary.

The original fixed-run design declared 20 earlier XNYS support sessions,
2021-08-11 through 2021-09-08, outside its 1,255-session evaluation count.
ADR 0206 supersedes that acquisition for the first Starter-backed program: the
first 20 available in-window sessions are feature warm-up instead.

## Source routes

- Massive Day Aggregates Flat Files are an independent bulk OHLCV cross-check. They
  require the separate S3 Access Key and Secret Key available in the Massive
  dashboard. The REST API key is not substituted.
- Grouped Daily REST is a bounded fallback and cross-check only for dates that
  the endpoint actually authorizes.
- dated, active All Tickers REST snapshots are the Identity source. Every page
  is retained in a sanitized immutable acquisition package before canonical
  Apply.

The later live control proved that the separate credential and current object
access work. The older 2021-09-09 object was denied under Starter. Flat Files
omit REST VWAP and its zero-volume path, so they are not silently substituted
for canonical REST packages.

## Execution boundaries

The exact-interval mode extends only the adjacent left edge of an already
contiguous EOD/Identity history. It refuses:

- a target whose endpoints are not XNYS sessions;
- a canonical latest session different from the frozen last session;
- a missing or mismatched first/last argument;
- a completed history extending outside the interval; or
- a non-adjacent continuation.

Each session completes Identity package, exact plan, Apply, formal readback,
then EOD package, exact plan, Apply, and formal readback. A bounded invocation
contains at most 20 sessions. Existing complete packages and canonical
partitions are reused only after formal validation.

Historical reference packages use ADR 0201's explicit reconstruction profile:
up to 1.0% stable-identifier collision observations may be retained as
ambiguous while remaining absent from Instrument and Resolver output. The
same profile uses ADR 0205's 2.0% malformed-row ceiling only for bounded
missing-type history; every such row remains rejected and later security type
is never projected backward. The prospective/current 0.1% collision and 1.0%
malformed ceilings are unchanged. A session above either historical ceiling
still stops, and no conflicting alias or later type may be selected merely to
keep the run moving.

The historical runner supplies each already-computed pre-state fingerprint to
its plan builder. The generic daily builder still computes its own value when
one is not supplied. Apply always recomputes the full-content fingerprint
under the publication lock; no cached or metadata-only value can authorize a
write.

Stocks Starter officially states unlimited API calls. The executor therefore
accepts an explicit serial interval from 0.25 through 15 seconds. It never
introduces concurrent provider requests. The first live pilot must use a small
batch and its observed response behavior determines whether the same interval
is retained. HTTP/provider failures remain visible; they are not hidden by
unbounded retries.

Offline validation and later family construction may use Dell CPU parallelism
after immutable source custody exists. Provider acquisition remains serial.

Massive Grouped Daily VWAP is normalized under ADR 0202 only when its source
scale exceeds the canonical scale of 10. The exact source package is retained;
the canonical row receives `vwap_scale_normalized`, and the session quality
summary records `vwap_scale_normalized_count`. OHLC and volume remain exact,
and the provider-neutral repository continues to reject over-scale input.

Massive provider symbols are case-sensitive. Under ADR 0203, EOD planning
binds the exact Grouped Daily symbol to the retained same-session Identity
source before resolution. Exact-symbol eligibility still comes from source
security-form evidence and the existing stable-ID policy; spelling patterns do
not establish eligibility. A mixed-case EOD symbol without exact same-session
source custody fails closed. The duplicate gate is never raised to merge
case-distinct securities.

Partitions published before ADR 0203 are not overwritten. The retained-package
census confirmed at least 1,862 missing resolved bars across 676 published
sessions, and current EOD V1 history therefore remains research-quarantined
until a separately versioned immutable correction or rebuild is complete.

## Historical operator command — do not run

The command is deliberately explicit and requires a clean repository:

```bash
scripts/admin/run-historical-research-backfill-continuous.sh \
  --data-root /data/trading-intelligence-platform \
  --package-root /home/hui/.local/state/trading-intelligence-platform/historical-backfill/five-year-2021-09-09--2026-09-09 \
  --target-first-session 2021-09-09 \
  --target-last-session 2026-09-09 \
  --request-interval-seconds 0.25 \
  --batch-size 20 \
  --execute
```

The package root must be a new or already formally reusable owner-controlled
directory. `/tmp` is accepted only for a bounded pilot. Persistent execution
accepts exactly one direct child of the fixed owner-only historical-backfill
base shown above; arbitrary home paths, nested targets, symlinks, foreign
ownership, and non-0700 directories fail closed. Each session uses the shared
governed `sessions/session_date=YYYY-MM-DD` acquisition-package and Apply-plan
roles, so the historical executor does not create a second custody convention.

The following external warm-up command is retained only for a future approved
deeper-history source program. ADR 0206 prohibits running it under the current
Starter program:

```bash
scripts/admin/run-historical-research-backfill-continuous.sh \
  --data-root /data/trading-intelligence-platform \
  --package-root /home/hui/.local/state/trading-intelligence-platform/historical-backfill/warmup-2021-08-11--2021-09-08 \
  --target-first-session 2021-08-11 \
  --target-last-session 2021-09-08 \
  --request-interval-seconds 0.25 \
  --batch-size 20 \
  --execute
```

Do not run this concurrently with the evaluation writer. Its canonical
EOD/Identity partitions use the same contracts, while its retained source
packages remain physically separate so the evaluation workspace name and
evidence are not rewritten or made misleading.

## Fixed-run completion check — historical

The legacy count-based planning CLI accepts at most 504 sessions. It is not a
post-run verifier for the frozen ADR 0196 1,255-session interval; use the
network-disabled five-year census and the exact-interval executor/readback
path for this scope.

EOD/Identity acquisition is complete only when:

1. the executor reports the frozen interval complete;
2. canonical EOD and Identity session indexes both contain all 1,255 sessions;
3. the normalized Identity source gap census is rerun;
4. every retained package and newly written partition passes formal readback;
5. a fresh five-year foundation census reports the exact family counts; and
6. conflicts, endpoint-denied dates, and source-route substitutions are
   preserved in a dated audit.

The stopped fixed run did not meet this checklist and will not be retried under
Starter. Active rolling-source completion is determined only by the ordinary
daily append followed by a fresh network-disabled ADR 0196 census.

Under ADR 0206, the first 20 available in-window sessions are formally excluded
from signals and performance as feature warm-up. A future deeper-history
program may instead activate the external support interval after separate
authorization and readback.

This milestone does not change research readiness or publish anything to OCI.
