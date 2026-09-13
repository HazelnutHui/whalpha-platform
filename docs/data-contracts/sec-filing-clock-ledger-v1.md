# SEC Filing-Clock Ledger V1

## Purpose

`sec-filing-clock-ledger/1.0` is the normalized availability bridge between a
sealed SEC Submissions census and the exact five-year Company Facts accession
population. It is not a listed-security mapping or a fundamental-value table.

## Row grain

One row exists for every unique in-range Company Facts accession. The business
key is `accession_number`. Rows are sorted by that key and preserve:

- Company Facts filed dates;
- Submissions filed dates;
- all distinct UTC acceptance timestamps;
- all distinct forms, source member names, and member CIKs;
- source row count;
- selected conservative availability timestamp;
- first eligible XNYS session;
- admission state and ordered reason codes; and
- an explicitly unresolved stable-instrument state.

An accession missing from Submissions remains present and quarantined. A
repeated accession remains one row while preserving its distinct evidence and
source row count.

## Availability rule

Methodology
`first_xnys_open_strictly_after_conservative_acceptance_v1` selects the sole
acceptance value or the latest of conflicting values. The eligible research
session is the first XNYS open strictly after that timestamp. Exact-midnight
source values are treated as time-quality warnings and cannot become eligible
on the same calendar date.

This is a conservative daily-research clock. It is not a claim about the first
tradable instant, filing interpretation latency, or intraday execution.

## Package and integrity

The immutable package contains `filing-clocks.parquet` and `manifest.json`.
The manifest binds both SEC source packages, both final censuses, the exact
range, implementation revision, XNYS calendar/version, availability
methodology, Parquet physical hash, deterministic logical row fingerprint,
row/count reconciliations, and zero-authority fields.

The owner-only custody root and package are mode `0700`; completed files are
mode `0400`. Publication is partial-directory first and atomic rename last.
Formal reread verifies path ownership, modes, manifest fingerprint, exact
Arrow schema, physical hash/size, sorted unique keys, logical fingerprint, and
all aggregate counts.

## Authority boundary

The package records zero stable-instrument resolutions, normalized Company
Facts occurrences, canonical writes, analytics, publications, deployments,
and scheduler changes. CIK and current ticker/exchange data cannot satisfy the
missing stable-security join.
