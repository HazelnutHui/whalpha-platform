# EOD Historical Window Architecture

## Purpose

The EOD history boundary reads a bounded set of completed canonical partitions for offline, point-in-time analysis. It does not fetch data, create aggregates, or change production Universe membership.

## Time Semantics

For analysis session `D`, same-day return analytics may use `D` and `D-1`, but liquidity eligibility uses exactly the 20 XNYS sessions before `D`, ending at `D-1`. `D` is structurally excluded so same-day volume cannot select the instrument that generated it.

V1 implements only `current_as_of_constituent_liquidity`: current analysis-date candidate IDs are evaluated over prior canonical bars. This is not a historical index or survivorship-free backtest. `point_in_time_historical_panel` is a distinct contract value but is not implemented; it will require each historical day's identity and Universe membership.

## Read Boundary

`EodReadRepository.read_history_sessions()` accepts an explicit, duplicate-free date tuple and reads only those partitions. Each partition must pass path containment and symlink checks, manifest/schema/session/count/content-fingerprint validation, physical Parquet SHA-256 calculation, stable instrument/session uniqueness, latest-revision validation, and identity-snapshot reference validation. A future identity reference fails closed.

History rows join across dates only by persisted `instrument_id`. Ticker is display metadata from that session's referenced Instrument Master. The history reader does not call a ticker resolver and cannot fall back to a latest resolver. A ticker change therefore preserves one stable-ID series, while ticker reuse cannot merge different instruments.

EOD schema 1.0 manifests persist the logical content fingerprint but not a separate physical Parquet hash. The reader validates decoded content against the manifest fingerprint and independently calculates/reports the physical SHA-256 for audit. No existing manifest is rewritten.

## Readiness

`EodHistoryWindowDescriptorV1` partitions every expected session into completed, missing, or corrupt/unavailable:

- `ready`: all 20 validated;
- `insufficient_history`: at least one partition is absent;
- `corrupt_or_unavailable`: an expected partition exists but fails validation.

An absent partition is a normal planning state. A corrupt partition blocks metric computation. Window-external files are not scanned and cannot block the bounded read.
