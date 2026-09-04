# Universe Membership V1

## Purpose

Universe Membership V1 records universe definitions and point-in-time daily membership decisions for market structure, discovery, portfolio override, and focus override scopes.

## Status

Partially Implemented — Daily Physical Contract and Complete-Base Shadow Pilot

The provider-neutral historical daily-decision record implements explicit
included/excluded/quarantined disposition, methodology and origin, exact
evaluated-base/source fingerprints, cutoff/evaluation timing, and reason/quality
state. Immutable PyArrow persistence now uses membership manifest `1.1`, which
proves the exact evaluated stable-ID base and complete three-state totals for
every Universe in the partition. A formal adapter reconstructs the reviewed
2026-08-19 full-base Primary/Secondary source as
`reconstructed_point_in_time`; the real Dell read-only pilot writes only to
`/tmp`.

Methodology `provider-form-complete-base-point-in-time-v2` additionally
reconstructs every stable ID in an exact same-day Identity snapshot from a
custody-validated, sanitized reference package. Its real 2026-09-03 Dell
shadow covered 9,979 IDs in both Universes and formally reread all 19,958 rows.
Primary produced 1,682 included / 8,235 excluded / 62 quarantined; Secondary
produced 1,797 / 8,107 / 75. One source collision was localized to one stable
ID instead of invalidating unrelated decisions. This remains `/tmp` evidence:
Universe Definition, durable source custody, multi-session canonical
publication, and a source for every retained historical date remain
unimplemented.

## Grain

Universe Definition grain: one universe definition for a methodology version and validity range.

Daily Universe Membership grain: one universe, instrument, and session date evaluation.

## Stable Identifier / Business Key

`universe_id` is the stable universe definition key.

Daily membership business key: `universe_id + instrument_id + session_date + methodology_version`.

## Universe Definition Fields

- universe_id
- name
- universe_type
- description
- methodology_version
- valid_from
- valid_to
- status
- schema_version

## Daily Universe Membership Fields

- universe_id
- instrument_id
- session_date
- is_member
- membership_source
- inclusion_reason_codes
- exclusion_reason_codes
- evaluated_at
- source_data_as_of
- methodology_version
- quality_status
- schema_version

Audit snapshot fields:

- price
- market_cap
- average_daily_dollar_volume_20d
- trading_history_days
- primary_exchange
- instrument_type

## Nullable Fields

- valid_to
- description
- inclusion_reason_codes
- exclusion_reason_codes
- audit snapshot fields when source data is unavailable

Missing critical inputs do not default to eligible.

## Enumerations

`universe_type` values:

- market_structure
- discovery
- portfolio_override
- focus_override

`membership_source` values:

- rule
- index_constituent
- portfolio_override
- focus_override
- manual_review

## Validation Rules

- A security can belong to multiple universes.
- Universe definitions and daily memberships are separate.
- Audit snapshot fields explain why membership was accepted or rejected.
- Audit snapshot fields are not the authoritative market-data source.
- Discovery membership is recalculated after EOD.
- Daily historical membership is retained.
- Current constituents must never be projected backward into history.
- Missing inputs produce exclusion or review reason codes.
- Override guarantees analysis eligibility only.
- Override does not indicate bullishness or recommendation.
- Portfolio and Focus memberships have distinct sources.
- Portfolio integration is not implemented in this phase.

## Temporal Semantics

`session_date` represents the exchange trading session being evaluated. `evaluated_at` uses UTC. `source_data_as_of` records the source-data cutoff used for membership evaluation.

## Revision Semantics

Universe methodology changes create new methodology versions. Daily membership history should remain point-in-time and auditable.

## Provider Mapping Boundary

Provider reference, price, market cap, and volume inputs may support membership evaluation, but the universe contract records the canonical membership decision and audit facts.

## Historical Implementation Prerequisites

The historical typed boundary now binds the evaluated-base fingerprint, every
source dataset fingerprint, origin
(`as_operated` or `reconstructed_point_in_time`), and included/excluded/
quarantined disposition totals required by the
[Historical Research Data Foundation V1](../architecture/historical-research-data-foundation-v1.md).
The physical partition manifest binds the evaluated-base count, exact stable-ID
set fingerprint, source fingerprints, and per-Universe disposition totals.
Every instrument in the declared evaluated base needs an explicit disposition;
omission is not exclusion, and missing critical evidence is not silently
converted to `is_member=false`.

The stable-ID base fingerprint is SHA-256 over compact JSON containing the
unique UUID strings in lexical order. Every Universe in one partition must
cover exactly that same base. A source policy's missing current/previous bar,
insufficient history, invalid input, outlier quarantine, or reviewed quarantine
maps to `quarantined`; explicit type, exchange, price, liquidity, or reviewed
exclusion maps to `excluded`.

When the retained source cutoff follows the evaluated session, every otherwise
valid reconstructed row is quality `warning` and carries
`reconstruction_source_cutoff_after_session`. Such a partition proves mechanics
but is not eligible as a no-look-ahead signal population.

The current offline census found validated retained reference packages for 279
of 303 canonical sessions. The exact 24-session gap spans the XNYS sessions
from 2026-07-17 through 2026-08-19. Retained `/tmp` packages are not canonical
source custody and are never copied into `/data` by the shadow. Known
non-target security forms, unsupported exchanges, price failures, and
liquidity failures are explicit exclusions. Missing/conflicting form evidence,
missing bars, insufficient history, material data-quality flags, and material
one-session return outliers are quarantined.

## Deferred Fields

- exact S&P 500/index constituent source
- final Discovery threshold calibration
- source revision reconciliation policy
- Portfolio integration details

## Non-Goals

- recommendation signals
- live portfolio ingestion
- market-data source of truth for price or volume
- provider adapter implementation
- canonical `/data` publication or active-pointer semantics
