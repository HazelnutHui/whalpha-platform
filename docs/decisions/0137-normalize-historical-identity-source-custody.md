# ADR 0137: Normalize Historical Identity Source Custody

- Status: Accepted
- Date: 2026-09-04

## Context

The 303-session canonical EOD/Identity index has 279 custody-valid retained
Identity reference packages and 24 physically missing package sessions. ADRs
0134 through 0136 prove that every retained package exactly reconstructs its
accepted same-day Identity families under one fingerprint-bound profile. The
packages remain spread across 12 owner-controlled directories below `/tmp`.
Their continued presence is not durable data custody.

Copying the one-gigabyte response-package tree into `/data` would preserve
transport envelopes, URLs, and request identifiers that are not research
facts, would contradict the established no-raw-response-by-default policy,
and would create a second opaque representation beside canonical Identity.
Keeping only the existing canonical Identity families is also insufficient:
they intentionally do not retain the provider security-form distinction and
complete source record needed for point-in-time Universe reconstruction.

A read-only census of every retained response artifact found one closed result
field set: `active`, `cik`, `composite_figi`, `currency_name`,
`last_updated_utc`, `locale`, `market`, `name`, `primary_exchange`,
`share_class_figi`, `ticker`, and `type`. No other result field occurs in the
279 packages.

## Decision

Create `historical-identity-source-custody/1.0` as a normalized source-
observation boundary. For each profile-bound session it stores one typed row
for every source result occurrence, including the complete twelve-field result
set, source page and row sequence, provider/session/observation time, and a
deterministic record fingerprint.

The completion manifest binds:

- the exact profile-map and per-session binding fingerprints;
- source package locator, manifest, content, observation time, request count,
  and every response artifact hash, byte count, and reconciled row count;
- all accepted canonical Identity-family fingerprints and selected rebuild
  profile;
- the fixed retained-field contract, record count, logical content
  fingerprint, Parquet hash, and materialization time; and
- explicit zero request, zero canonical-write, zero membership-write, and
  no-authority states.

The normalized projection excludes response-wrapper URLs, request identifiers,
provider response bodies, credentials, and Authorization material. The
manifest retains page-level physical hashes, counts, status, and pagination
presence without retaining those wrapper values. Unexpected result fields,
unsupported field types, secret-bearing material, page/count mismatch,
package/profile drift, Identity mismatch, symlinks, writable completed files,
unexpected files, or changed bytes fail closed.

Physical candidates use the future Dell-root-relative layout:

```text
market-data/provider-identity-reference-observation/
  schema_version=1/provider=<provider>/as_of_date=YYYY-MM-DD/
    part-00000.parquet
    manifest.json
```

The first implementation may write only below an explicit owner-only `/tmp`
root. One invocation is finite at no more than 303 bound sessions and four
socket-disabled workers. It is resumable and idempotent by formally rereading
an identical completed partition, but it has no direct `/data` writer. A later immutable
copy plan must bind the candidate bytes, exact absent targets, and current
`/data` inventory before a separately reviewed Apply.

This dataset is an internal `point_in_time_identity` source observation with
canonical no-auto-expiry retention. Because the packages were observed after
their historical sessions, it records
`outcome_reconciliation_only`; durable custody does not retroactively claim
that the source was known at the historical signal cutoff.

## Consequences

- All retained source result facts survive loss of `/tmp` without preserving
  raw response envelopes or duplicating canonical Identity Parquet.
- Page and package hashes preserve the migration evidence chain even though
  the original response bodies are not promoted into `/data`.
- Historical membership can later consume the normalized records plus the
  independently retained canonical Identity families and type catalog. That
  consumer change requires exact equivalence proof before broad reconstruction.
- Moving packages no longer needs to be hidden behind a changed ADR 0136
  locator. The normalized custody manifest explicitly terminates that
  temporary locator chain at a new immutable source-observation fingerprint.
- The 24 missing sessions remain a separate acquisition or alternative-source
  queue. Existing 2026-08-14 provider-security evidence may be reviewed as an
  alternative source, but is not silently counted as an Identity package.
- No Historical Coverage, daily Universe Membership, strategy readiness,
  Production, scheduler, model, Universe, or public-serving state changes.

## Alternatives Considered

### Copy the complete package directories into `/data`

Rejected because it retains transport envelopes rather than a governed source
family and conflicts with the no-raw-response-by-default policy.

### Keep relying on `/tmp`

Rejected because temporary storage is not durable, recoverable research
custody.

### Retain only provider type and exchange for canonical instruments

Rejected because it loses excluded, ambiguous, duplicate, and future-use
source facts and prevents independent reconstruction of the observation set.

### Reuse Provider Security Evidence Snapshot V1 unchanged

Rejected because that contract assumes its type catalog and All Tickers
observations were captured in one operation date. Historical normalization
reuses a separately observed catalog and must not collapse those clocks.
