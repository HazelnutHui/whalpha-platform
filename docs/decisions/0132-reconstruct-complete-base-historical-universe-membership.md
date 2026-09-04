# ADR 0132: Reconstruct Complete-Base Historical Universe Membership

## Status

Accepted.

## Date

2026-09-04.

## Context

Canonical Dell EOD and same-session Identity now cover 303 contiguous XNYS
sessions, but historical Universe Membership remains absent from `/data`. The
single 2026-08-19 pilot consumes a reviewed full-base publication whose
evaluated base contains only the CS/ADRC union. It cannot safely reconstruct
every daily decision or explain whether a non-member was explicitly excluded
or simply lacked evidence.

Custody-validated, sanitized Identity reference packages remain available in
`/tmp` for 279 of the 303 canonical sessions. They retain the provider's
point-in-time security-form and exchange fields that canonical Instrument
Master intentionally normalizes away. The 24 sessions from 2026-07-17 through
2026-08-19 do not have a retained package. These temporary packages are useful
for an offline mechanics proof, but are not durable canonical source custody.

## Decision

Add a network-disabled, `/tmp`-output-only historical membership shadow that:

- formally rereads the exact same-session Identity and EOD partitions;
- formally validates the sanitized Identity package and reuses only the
  completed provider type catalog as a code dictionary;
- requires that the package exactly rebuild the accepted same-day Instrument
  Master, provider Identity, and ticker Resolver logical fingerprints;
- evaluates every stable ID in the same-day canonical Instrument Master for
  both Primary and Secondary, rather than retaining only included securities;
- treats CS as provisionally eligible for both Universes and ADRC as
  provisionally eligible only for Secondary, while preserving the existing
  issuer-structure limitation;
- explicitly excludes known non-target security forms, unsupported exchanges,
  prior closes below USD 5, and 20-session median dollar-volume proxies below
  USD 20 million;
- quarantines missing or conflicting security-form evidence, missing bars,
  incomplete 20-session history, material data-quality flags, and one-session
  close moves of at least 100% or at most -50%; and
- binds the membership partition to the package, Identity, type catalog,
  current/trailing EOD partitions, derived evidence, and history descriptor
  fingerprints.

Provider mapping ambiguity, stable-identifier collision, and canonical
evidence conflict are localizable: affected or unevidenced stable IDs are
quarantined without discarding unrelated instruments. Empty catalogs,
insufficient raw coverage, excessive requests, failed raw reconciliation, and
sub-threshold Identity linkage remain whole-session failures.

The methodology is
`provider-form-complete-base-point-in-time-v2`. Because retained historical
packages were fetched after their stated sessions, resulting rows carry
`reconstruction_source_cutoff_after_session` and are mechanics-only. A later
formal publication requires durable source custody or an equivalent reviewed
source envelope, completion of the 24 missing sessions, multi-session
efficiency review, and a separate canonical apply decision.

## Consequences

- A one-record collision no longer converts an otherwise reconstructable day
  into an all-or-nothing loss; the uncertainty remains visible and isolated.
- Every Universe partition can prove explicit included, excluded, and
  quarantined coverage of the exact same stable-ID base.
- Raw provider bodies remain outside `/data` and are neither logged nor copied.
- No network request, credential read, canonical data write, active-pointer
  change, publication, deployment, or scheduler action is added to the shadow.
- The 279 retained packages are evidence availability, not 279 completed
  canonical membership partitions. The 24 missing package sessions remain a
  precise blocker rather than being guessed or backfilled from current state.

## Alternatives Considered

### Reuse each day's normalized Instrument Master type

Rejected because it collapses CS and ADRC and cannot reproduce the active
Primary/Secondary security-form distinction.

### Persist only CS and ADRC decisions

Rejected because absence would remain indistinguishable from explicit
non-target-form exclusion or missing evidence.

### Fail an entire session for any mapping collision

Rejected because a stable-ID-complete quarantine ledger can contain the
uncertainty without discarding unrelated, independently evidenced records.

### Copy retained raw packages into canonical storage

Rejected because raw-provider-body retention is not the current data-governance
policy and `/tmp` package custody is not a canonical publication contract.
