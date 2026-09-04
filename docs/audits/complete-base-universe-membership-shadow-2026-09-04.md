# Complete-Base Universe Membership Shadow Audit — 2026-09-04

## Scope

This audit proves one real, disconnected 2026-09-03 reconstruction on the Dell
workstation. It read canonical `/data` and one custody-validated sanitized
Identity package, but wrote only a new `/tmp` root. Network sockets were
disabled for the complete build and formal reread.

The audit does not authorize a provider request, raw-response retention,
canonical membership publication, Historical Coverage, model research,
Snapshot generation, bundle construction, deployment, or scheduler change.

The validated package also exactly rebuilt all three accepted 2026-09-03
Instrument Master, provider Identity, and ticker Resolver logical
fingerprints; a merely plausible or date-labelled package is insufficient.

## Source coverage census

- Canonical EOD / same-day Identity sessions: 303, 2025-06-23 through
  2026-09-03.
- Unique formally valid retained Identity reference packages: 279.
- Missing packages: 24 XNYS sessions, exactly 2026-07-17 through 2026-08-19.
- Duplicate or out-of-scope retained package sessions: zero.
- The retained packages are ephemeral `/tmp` evidence and not canonical source
  custody.

## Real 2026-09-03 result

| Evidence | Result |
| --- | --- |
| Methodology | `provider-form-complete-base-point-in-time-v2` |
| Origin | `reconstructed_point_in_time` |
| Raw provider records | 13,153 |
| Canonical provider evidence | 9,978 |
| Same-day evaluated stable-ID base | 9,979 |
| Complete membership rows | 19,958 |
| Localized source conflicts | one stable-identifier collision affecting one stable ID |
| Source cutoff | `2026-09-04T07:05:33.059186Z` |
| Evaluated-base fingerprint | `489d05cee32a9dc57f02d4cfab60ebdf6a3ae1fb2ff2103a48f05dcffa1252c9` |
| Logical fingerprint | `c3fe7e7d190abbf0e711a31df52704edaed4efeda06a8d52571c4b45c60d7c02` |
| Parquet SHA-256 | `a20cf85d30b879c5683ba6acff12366881570465dcff5fee066560987d120c0e` |
| Parquet bytes | 456,843 |
| Manifest bytes | 2,039 |

Disposition reconciliation:

| Universe | Included | Excluded | Quarantined | Evaluated |
| --- | ---: | ---: | ---: | ---: |
| Primary | 1,682 | 8,235 | 62 | 9,979 |
| Secondary | 1,797 | 8,107 | 75 | 9,979 |

Primary is a subset of Secondary by policy. These counts are a reconstructed
2026-09-03 shadow and are not the active 2026-08-19 Production membership.
Every otherwise usable row is later-known warning evidence because the source
cutoff follows the evaluated session.

## Determinism and performance

The final implementation reuses one formal 20-session EOD read for both
liquidity and decision construction. The current session is also read once.
The 21 EOD component identities are folded into one deterministic source
envelope instead of repeating every component hash on all 19,958 rows.

Two independent `/tmp` builds with the same source and evaluation clock
produced the same logical fingerprint and physical Parquet SHA-256. The final
post-hardening idempotency run completed in 149.72 seconds, used 975,264 KiB
maximum resident memory, received no socket messages, wrote zero bytes, and
reported zero external requests and zero canonical data writes.

Source compilation, the focused shadow regression suite, and all 2,008 backend
tests passed. The full suite emitted only the two unchanged dependency
deprecation warnings.

## Remaining blockers

1. Define durable, minimal source custody without treating the retained
   `/tmp` packages as authority or copying raw provider bodies by default.
2. Resolve only the exact 24 missing sessions through a separately reviewed
   acquisition or equivalent evidence source.
3. Replace repeated single-day execution with one shared formally validated
   panel and deterministic rolling 20-session calculations before a 279-day
   shadow batch.
4. Reconcile every daily partition, cutoff, source envelope, and cross-day
   Primary/Secondary invariant in `/tmp`.
5. Review canonical publication separately. Until then `/data` correctly has
   no historical Universe Membership family.
