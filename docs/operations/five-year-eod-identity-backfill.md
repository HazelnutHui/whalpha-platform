# Five-Year EOD and Identity Backfill

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

The first evaluation session's trailing-liquidity Membership calculation needs
20 earlier XNYS support sessions: 2021-08-11 through 2021-09-08. They are a
separate warm-up extension, not part of the 1,255-session evaluation count.
The current exact-interval run intentionally stops at 2021-09-09; support
acquisition follows as a separately measured route after the nominal interval
and must not be hidden by moving the evaluation boundary.

## Source routes

- Massive Day Aggregates Flat Files are the preferred bulk EOD source. They
  require the separate S3 Access Key and Secret Key available in the Massive
  dashboard. The REST API key is not substituted.
- Grouped Daily REST is a bounded fallback and cross-check only for dates that
  the endpoint actually authorizes.
- dated, active All Tickers REST snapshots are the Identity source. Every page
  is retained in a sanitized immutable acquisition package before canonical
  Apply.

The 2026-09-10 live Flat File pilot stopped before its first S3 request because
the separate credential file was absent. This is a route-specific missing
configuration, not evidence that the Starter entitlement is unavailable.

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
prospective/current 0.1% ceiling is unchanged. A session above the historical
ceiling still stops, and no conflicting alias may be selected merely to keep
the run moving.

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

## Operator command

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

## Completion check

EOD/Identity acquisition is complete only when:

1. the executor reports the frozen interval complete;
2. canonical EOD and Identity session indexes both contain all 1,255 sessions;
3. the normalized Identity source gap census is rerun;
4. every retained package and newly written partition passes formal readback;
5. a fresh five-year foundation census reports the exact family counts; and
6. conflicts, endpoint-denied dates, and source-route substitutions are
   preserved in a dated audit.

The later Membership stage additionally requires formal readback of the 20
support sessions. A missing support session blocks only the earliest dependent
Membership sessions; it does not relabel the rest of the acquired five-year
EOD/Identity interval incomplete.

This milestone does not change research readiness or publish anything to OCI.
