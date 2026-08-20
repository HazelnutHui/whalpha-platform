# Reviewed Eligibility Override V1

This provider-neutral shadow contract records completed human review without changing canonical security evidence or activating a production Universe.

Each immutable row is keyed by `override_id` and stable `instrument_id`. It records a half-open effective interval, `exclude`/`quarantine`/`allow`, asserted security form and issuer structure, evidence grade, source reference and document date, reviewer identifier, reason code/text, and UTC creation time. Ticker is not an identity field.

## Gates

- `effective_from <= session < effective_to`; an absent end is open-ended.
- Source document date cannot be later than `effective_from`; current evidence cannot be backfilled into history.
- Duplicate override IDs, duplicate `(instrument_id, effective_from)` keys, overlapping periods, and conflicting active decisions fail closed.
- Only authoritative or already-reviewed evidence can form a row. Names, ticker, CIK, FIGI, and descriptions are not sufficient alone.
- `allow` can preserve a member that already passed upstream security-form and trailing-liquidity gates. It cannot add a failed, missing-history, missing-bar, below-price, or below-liquidity instrument.
- `exclude` and `quarantine` may only remove an upstream passed member.

The Parquet schema is explicit and extra fields are forbidden. Ordering and business fingerprints are stable by ID/effective date; operational creation time does not change membership identity.

## Completion boundary

The override partition and pre-activation decision partition are staged and reread before atomic rename. A separate logical manifest is published last and references the completed Trailing Liquidity V1 source, Legacy calculation inputs, component row counts, content fingerprints, physical Parquet hashes, and final A/B membership fingerprints. Existing targets and symlinks are rejected.
