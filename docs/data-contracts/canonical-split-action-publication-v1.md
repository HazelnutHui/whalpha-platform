# Canonical Split Action Publication V1

Contracts:

- `canonical-split-action-publication/1.0`
- `canonical-split-action-apply-plan/1.0`
- canonical row schema `1.0`

## Purpose and scope

This publication is the first provider-neutral canonical Corporate Action fact
family. Version 1 is deliberately `split_only`: stock splits, reverse splits,
and stock dividends represented by exact positive Decimal ratios. It is not a
complete Corporate Action, dividend total-return, Adjustment Ledger, or
research-performance dataset.

## Canonical row

Each row preserves:

- deterministic canonical action ID and stable `instrument_id`;
- action type, effective date, split-from and split-to ratios;
- provider, provider action identity and revision, canonical revision;
- exact source publication and event-group fingerprints;
- event-group size and active or quarantined disposition;
- first-observed and ingestion timestamps; and
- explicit quality, unavailable-source-time, and outcome-only flags.

A one-row stable-ID/effective-date group must be active and valid. A multi-row
group must be quarantined and pending review. The reader rejects mixed group
fingerprints, inconsistent group sizes, duplicate source/canonical identities,
non-split types, non-positive ratios, unordered rows, and date or source
publication drift.

Unresolved provider rows are not converted to canonical rows. The manifest
retains their count and an ordered possible-impact quarantine set; assignment
remains false.

## Physical custody

The immutable target is:

```text
/data/trading-intelligence-platform/market-data/
  canonical-corporate-actions/schema_version=1/action_scope=split/
  coverage_id=<publication-logical-fingerprint>/
    actions.parquet
    manifest.json
```

The directory is `0755` and both files are `0644`. The owner-only candidate
uses `0700` and `0400`. The manifest binds the Parquet size, physical SHA-256,
logical row fingerprint, source marker, candidate identity, counts, date range,
quarantine evidence, and every non-authority boundary.

Parquet Decimal scale is physical only. Logical hashing normalizes numerically
equivalent Decimal representations so `1` and `1.000000000000000000` cannot
create a false content change.

## Plan and Apply

The plan binds the clean source revision, original split candidate, generated
publication candidate, exact two artifacts, absent content-addressed target,
whole `/data` pre-state fingerprint, and zero external/write authority.

Apply re-reads every source and candidate, takes the shared Dell data lock,
requires the exact pre-state, stages the two files, fsyncs them, atomically
renames the complete directory, formally rereads the canonical result, and
proves the outside-target inventory unchanged. An exact already-published
target is a zero-write verified recovery; partial, symlinked, conflicting, or
drifted state fails closed.

## Interpretation boundary

`bounded_query_snapshot_only` and `outcome_reconciliation_only` are mandatory.
Absent events do not imply a neutral factor. Full action-type coverage,
historical availability/revision completeness, Adjustment Ledger publication,
Historical Coverage, research use, analytics, and deployment all remain false.
