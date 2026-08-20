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
