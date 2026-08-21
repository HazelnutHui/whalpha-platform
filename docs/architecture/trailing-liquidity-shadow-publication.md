# Trailing Liquidity Shadow Publication Architecture

## Flow

The offline service validates the latest canonical EOD session, builds the prior 20 XNYS-session descriptor, rereads all bounded EOD partitions and their same-day identity references, and reconstructs the Provider-Classified Candidate A/B membership from the completed evidence snapshot.

The calculation service emits one union metric table and one candidate decision table. The Parquet repository validates explicit Arrow schemas, Pydantic rows, deterministic ordering, business-key uniqueness, reference integrity, content fingerprints, and physical SHA-256 values.

## Paths

- `market-data/derived/trailing-liquidity-metrics/schema_version=1/analysis_session=YYYY-MM-DD`
- `market-data/derived/trailing-liquidity-shadow-decisions/schema_version=1/analysis_session=YYYY-MM-DD`
- `market-data/snapshots/trailing-liquidity-shadow/analysis_session=YYYY-MM-DD`

The snapshot manifest is the final logical completion marker. Derived paths are separate from canonical EOD, identity, and provider-evidence paths.

## Publication safety

The administrator CLI defaults to dry-run and writes only with `--apply`. It requires explicit analysis date, membership-evidence date, input fingerprints, UTC calculation timestamp, and absolute data root. It contains no provider transport or credential-loader dependency.

All target and staging paths are contained under a nonsymlink data root. Existing identical completed content is idempotent; partial, corrupt, or conflicting targets fail closed. Both component partitions are fully staged before rename, the logical marker is renamed last, and newly renamed targets are removed if the transaction fails before completion.

This publication does not activate a Universe or modify API, Dashboard, frontend, snapshots, bundles, or deployment state.

## Full-Base Scope Correction

The original V1 union was limited to 1,864 records already admitted by the prior one-session dollar-volume screen. The corrected builder never consumes Legacy, Activation, a Dashboard snapshot, ticker names, or available-bar lists as its candidate source. It starts from completed canonical provider evidence: 4,193 `CS` records for Primary and 4,565 `CS`/`ADRC` records for Secondary.

The corrected family publishes five Parquet components—metric/status facts, complete policy decisions, selected memberships, old-versus-corrected diffs, and funnel stages—plus a final logical manifest. Each of the 4,565 Secondary-base stable IDs has a metric/status row; each A/B base ID has exactly one mutually exclusive disposition. Source references bind the publication to the 20 EOD partitions, security evidence, immutable V1 publication, and reviewed overrides.

Paths use `trailing-liquidity-full-base-*` dataset names and the logical `trailing-liquidity-full-base-scope-review` family. This is a new shadow boundary, not an overwrite of V1.

The 2026-08-20 authorized publication remained fail-closed before staging: a remaining metric Decimal exceeded the approved `decimal128(38,10)` scale. The repository did not round or truncate it and no target was created.

The subsequent offline physical-contract review found two affected metric medians and no affected `previous_close` values. Canonical close and volume are each `decimal128(38,10)`: their product can require precision 76/scale 20, while an exact even median can require precision 77/scale 21. Arrow `decimal256` supports at most precision 76, so it cannot cover the complete input contract. The unpublished full-base family therefore retains `previous_close` as `decimal128(38,10)` and stores each median as an explicit Arrow struct containing sign, an unsigned big-endian binary coefficient, and the Decimal exponent. The reader reconstructs the logical Decimal exactly; deterministic fingerprints encode binary coefficients as canonical hexadecimal solely for hashing.

The exact-median physical gate permits at most precision 77, scale 21, and 56 integer digits. Errors identify dataset, field, stable instrument ID, ticker, observed precision/scale, and approved precision/scale. This is the first-publication physical schema for the still-unpublished V1 family, so no schema version is bumped and no completed schema is silently changed.

### Arithmetic context independence

Canonical close and volume are converted from their Decimal tuples to signed integer coefficients before arithmetic. Daily products use arbitrary-precision integer multiplication; the 20 products are ordered as exact integers at a common scale; and the middle pair is averaged by integer parity, adding one scale digit only when the sum is odd. Constructing the boundary Decimal from `(sign, digits, exponent)` does not consult Python's process-global Decimal context.

Price and USD 20M comparisons therefore cannot set or silently ignore `Inexact`/`Rounded`. Material-return ratio gates use cross-multiplied coefficients. Audit-only return analytics can require non-terminating division; those calculations use a new explicit local precision-78 context (`2 × decimal128 precision 38 + 2`) with `ROUND_HALF_EVEN` and explicitly nontrapping local `Inexact`/`Rounded`. Caller traps and flags are never inherited, and local flags are discarded without leaking to the process context.

EOD fingerprint Decimal encoding is likewise tuple-based: it canonicalizes sign, coefficient, exponent, zero, and trailing numeric zeroes without `normalize`, float conversion, rounding, or quantization. This preserves all existing stored EOD fingerprints under process precisions 9, 28, and 50 and with caller traps enabled.

The separate `fractions.Fraction` dry-run oracle now rebuilds provider-type eligibility, exchange eligibility, bar presence, previous close, every daily product, complete-window median, price/liquidity/outlier gates, reviewed overlay, decision reasons, membership, and fingerprints directly from raw canonical reader inputs. It does not consume full-base metric rows or other production-derived eligibility state.
