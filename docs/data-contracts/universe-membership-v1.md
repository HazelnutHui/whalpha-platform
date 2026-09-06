# Universe Membership V1

## Purpose

Universe Membership V1 records universe definitions and point-in-time daily membership decisions for market structure, discovery, portfolio override, and focus override scopes.

## Status

Partially Implemented — Daily Physical Contract, Complete-Base V3 Mechanics,
and Knowledge-Time Gate

The provider-neutral historical daily-decision record implements explicit
included/excluded/quarantined disposition, methodology and origin, exact
evaluated-base/source fingerprints, cutoff/evaluation timing, and reason/quality
state. Immutable PyArrow persistence now uses membership manifest `1.1`, which
proves the exact evaluated stable-ID base and complete three-state totals for
every Universe in the partition. A formal adapter reconstructs the reviewed
2026-08-19 full-base Primary/Secondary source as
`reconstructed_point_in_time`; the real Dell read-only pilot writes only to
`/tmp`.

Methodology `provider-form-complete-base-point-in-time-v3` additionally rereads
canonical normalized Identity source custody, exactly rebuilds all three
Identity families, and reconstructs every stable ID in the accepted same-day
snapshot. Disconnected mechanics cover 302 source-available sessions and
5,611,048 formally reread decisions. The source-revised 2026-08-13 and
2026-08-19 dates remain absent rather than approximated.

ADR 0151 adds a separate offline knowledge-time assessment. A partition is
signal-eligible for a next-session-open strategy only when its bound Identity
source is contemporaneous and the full source cutoff and Membership evaluation
both precede that exact XNYS open. The 2026-09-04 temporary partition passes;
the corrected 2026-09-03 historical partition remains outcome-only. Neither
assessment publishes canonical Membership or Historical Coverage.

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

`session_date` represents the exchange trading session being evaluated.
`evaluated_at` and `source_data_cutoff` use UTC. For next-open research, the
session close is the market-information boundary while the immediate next XNYS
open is the strict latest permissible source/evaluation boundary. These are
different clocks and both remain explicit.

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

When the retained source cutoff follows the evaluated session date, every
otherwise valid reconstructed row is quality `warning` and carries
`reconstruction_source_cutoff_after_session`. ADR 0151 then makes the actual
research-use decision separately: a later calendar date can still be eligible
when a direct daily source and the completed evaluation both precede the next
XNYS open; a historical/outcome-only source cannot.

Canonical normalized source custody now covers 302 of 304 EOD/Identity
sessions. Custody validity is necessary but not sufficient: each source must
exactly reproduce the accepted Instrument Master, provider Identity, and
ticker Resolver fingerprints, then remain bound into Membership lineage.
Known non-target forms, unsupported exchanges, price failures, and liquidity
failures are explicit exclusions. Missing/conflicting form evidence, missing
bars, insufficient history, material quality flags, and material return
outliers are quarantined.

Offline batch execution is limited to five adjacent XNYS analysis sessions.
The completion index discovers dates, but every current/trailing EOD partition
that feeds a decision is fully read and validated once. Every successful daily
partition keeps its own base, source envelope, cutoff, and formal reread. A
package-specific mismatch cannot become an exclusion and cannot contaminate a
different session.

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
