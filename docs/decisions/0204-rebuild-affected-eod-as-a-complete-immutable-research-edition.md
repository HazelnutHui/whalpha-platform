# ADR 0204: Rebuild affected EOD as a complete immutable research edition

- Status: Accepted
- Date: 2026-09-10

## Context

ADR 0203 corrected Massive's case-sensitive symbol handling for new EOD
mapping, but at least 1,862 resolved bars are already known to be absent from
immutable EOD V1 partitions. A sparse overlay would save storage, but it would
make every future research reader permanently merge two datasets and could
hide unmeasured differences outside the known missing-row class. Rewriting V1
would destroy reproducibility and violate the completed-partition contract.

The Dell workstation has sufficient storage for another bounded five-year EOD
family. Operational simplicity and independently verifiable research inputs
are more valuable here than avoiding a duplicate copy of one compact daily-bar
family.

## Decision

Build a complete immutable **Reconciled EOD Edition V1** beside, never over,
canonical EOD V1. The edition is a research input candidate, not a Production
replacement or active source merely because some partitions exist.

The edition has these boundaries:

- every included session is a full EOD cross-section produced by one frozen
  provider mapper and exact same-session Identity evidence;
- retained original Grouped Daily packages are preferred; any reacquired
  source package is separately immutable and records its later observation
  time rather than pretending to be the original response;
- each session binds the source-package fingerprint, canonical Identity
  fingerprint, exact Identity-source fingerprint, mapper revision, source
  provenance class, and full canonical content fingerprint;
- the session reconciliation compares the rebuilt edition with EOD V1 and
  separately counts added, absent, and economically changed business keys;
- the known ADR 0203 repair may add missing resolved bars, but removal or an
  economic-value change never auto-passes as the same defect;
- a session with missing exact source, unresolved provenance, failed quality
  gates, or an unexplained diff remains incomplete and quarantined;
- independent source-family blockers are reported cumulatively; price-source
  reacquisition may proceed for an exact missing Grouped Daily package even
  when the session remains separately blocked by absent Identity source
  custody, without granting build readiness;
- completed session partitions are immutable and resumable; and
- one interval manifest is published last only after all required evaluation
  and declared warm-up sessions pass formal reread and reconciliation.

No reader may consume an edition by scanning whatever session directories
happen to exist. Research must name the exact edition ID and final interval
fingerprint. Candidate, Production analytics, Dashboard, and website readers
continue using their existing inputs until a separate admission and activation
decision explicitly changes them.

## Physical direction

The logical row contract remains EOD Price Bar V1. Physical custody is a
separate edition family, keyed by immutable `edition_id`, rather than
mislabeling a provider-mapping correction as a new row-schema version.

```text
<root>/market-data/reconciled-eod-price-bar-editions/
  contract_version=1/
    edition_id=<frozen-id>/
      session_date=YYYY-MM-DD/
        part-00000.parquet
        manifest.json
      interval-manifest.json
```

The final interval manifest is the only completion marker. Its absence means
the edition is assembling and ineligible, not partially complete.

## Consequences

- Existing EOD V1 stays readable and reproducible for current Production.
- Research gets one uniform full-session family instead of a permanent sparse
  overlay merge.
- Storage increases, but the bounded five-year scope is acceptable on Dell and
  avoids a more complex consumer contract.
- Reacquired provider data cannot silently masquerade as original custody;
  value differences receive a distinct disposition.
- The edition fixes only the price-family mapping defect. It does not establish
  lifecycle, corporate-action, Membership, adjustment, or fundamentals
  completeness.

## Rejected alternatives

- **Overwrite EOD V1:** rejected because completed canonical partitions are
  immutable.
- **Sparse additions-only overlay as the permanent research source:** rejected
  because all consumers would inherit merge logic and unscanned defects could
  remain hidden.
- **Treat `schema_version=2` as the correction:** rejected because the logical
  EOD row schema did not change; source/mapping edition and schema version are
  different concepts.
