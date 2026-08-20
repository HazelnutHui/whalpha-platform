# Universe Pre-Activation Review Architecture

The offline service formally rereads the completed Trailing Liquidity V1 publication for analysis session 2026-08-19, its 20 prior XNYS sessions, and the 2026-08-14 provider security evidence. It independently reconstructs the Legacy Liquid Screen from the completed 2026-08-13/14 canonical EOD pair using the existing stable-ID rule.

Candidate A permits provider `CS`. Candidate B uses the existing stable ID `provider_classified_common_shares_plus_adrs_shadow_v1` and permits `CS` plus separately counted `ADRC`. Ticker is display-only.

Reviewed Eligibility Override V1 is applied only after a candidate has passed the published trailing-liquidity decision. `exclude` and `quarantine` remove; `allow` never bypasses upstream hard gates. The service produces one decision row per base-passed `(universe_id, instrument_id)` and deterministic final membership fingerprints.

## Paths

- `market-data/derived/reviewed-universe-eligibility-overrides/schema_version=1/analysis_session=YYYY-MM-DD`
- `market-data/derived/universe-pre-activation-review/schema_version=1/analysis_session=YYYY-MM-DD`
- `market-data/snapshots/universe-pre-activation-review/analysis_session=YYYY-MM-DD`

These are derived shadow artifacts. They do not modify canonical EOD, identity, provider evidence, the Trailing Liquidity publication, production Universe settings, API responses, Dashboard assets, or deployment state.
