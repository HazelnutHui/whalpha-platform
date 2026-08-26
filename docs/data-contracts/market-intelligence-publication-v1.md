# Market Intelligence Publication V1

## Status and scope

Implemented as an approval-bound Production contract. Active publication
`2026-08-24T043223Z-aee1a6ab0f67` is the exact user-approved 2026-08-24
`stale_review`: expected session 2026-08-25, lag one. It is not an ordinary
fresh publication and does not authorize reuse of the exception for another
session or release.

The publication contains one language-neutral Market Regime & Opportunity Map
payload shared by the English and Simplified Chinese interfaces. Locale never
enters this contract or its fingerprints.

## Immutable layout

```text
<data-root>/market-data/analytics/market-intelligence/
  schema_version=1/revision=market-regime-opportunity-map-v1/
    analysis_session=<YYYY-MM-DD>/publication_id=<id>/
      market-intelligence.json
      manifest.json
<data-root>/market-data/analytics/market-intelligence-active/active.json
```

A completed directory contains exactly two regular immutable files. Extra
files, symlinks, path traversal, non-canonical JSON, or any physical/logical
hash mismatch fail closed. Completed targets are never overwritten or repaired.

## Payload and manifest

Contract `market-intelligence-publication/1.0` binds:

- schema/calculation versions, revision, publication ID, and analysis session;
- the exact 26-session EOD ledger, latest EOD physical/business/content hashes,
  same-day Identity logical fingerprint, and history fingerprint;
- Activation pointer/logical fingerprints, Primary-first catalog, counts, and
  membership fingerprints;
- Phase 1a, Phase 1b, Phase 2, and preview aggregate logical fingerprints;
- both Universe regime ledgers, state history, five dimensions, missingness,
  30 ETFs, all 16 pairs, 5/10/20 metrics, and 336 relationship-history rows;
- `language_neutral=true`, locales `en`/`zh`, zero external requests, no
  credentials, and no raw provider payload.

`generated_at` and `publication_id` do not alter payload logical content, but
remain physically bound by payload SHA and manifest. JSON is NFC-normalized,
key-sorted, compact, newline-terminated, and rejects NaN/Infinity.

## Formal reader and API

The reader validates pointer identity, namespace, exact files, canonical bytes,
SHA-256, logical fingerprints, source lineage, Universe order/counts, and pair
counts. An absent pointer is unavailable; a corrupt pointer never falls back.

`TIP_ENABLE_MARKET_INTELLIGENCE_ROUTES=true` validates the active release once
at FastAPI startup and creates an immutable in-memory view. Requests never scan
EOD or recalculate analytics. With no explicit flag routes remain absent;
preview and formal modes are mutually exclusive.

Any analytics, lineage, ordering, nullability, or meaning change requires a new
contract/calculation version and fingerprint. Translation changes do not.

## Explicit review deployment sub-contract

Normal activation remains `fresh` only: lag zero and exact expected/actual
session equality. Contract `production-review-deployment/1.0` adds one
deliberately non-general exception for the user-approved review release. It is
valid only for analysis/actual session `2026-08-24`, expected session
`2026-08-25`, lag one, and the exact explicit acknowledgement token. The
authorization is stored in the language-neutral payload, manifest, immutable
reference, pointer, and approval plan, so a changed date, lag, source, plan,
or current state fails closed.

Review responses use `data_status=stale_review`; they never claim `fresh`.
English and Chinese render the same authorization and analytics payload. This
sub-contract is not an `allow-stale` switch and cannot authorize any other
session or future release.

## Contract 1.1 Candidate extension

Repository source also implements `market-intelligence-publication/1.1` while
retaining formal 1.0 reading and rollback compatibility. Version 1.1 keeps the
same immutable two-file layout, pointer version, namespace, and revision, and
adds a mandatory language-neutral Candidate source binding and bounded
`opportunity-candidate-publication/1.0` analytics object.

The plan version becomes 1.1 and freezes the exact `/tmp` Candidate audit,
audit/Oracle/equivalence lineage, and Candidate analytics fingerprint. Apply
and verify-then-link reread that approved audit under the existing guarded
publication flow. A 1.0 plan cannot activate a 1.1 payload. The active
Production publication remains 1.0 until a new exact freshness or stale-review
authorization is approved; the existing 2026-08-24 exception is not inherited.
