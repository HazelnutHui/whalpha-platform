# Quant Research Reusable Artifact Registry V2

## Purpose

`quant-research-reusable-artifact-registry/2.0` is the append-only successor to
the V1 policy registry. It records the first real reusable research artifact:
the outcome-blind Market-State panel that passed the frozen qualification and
independent exact replay on 2026-09-16.

V1 remains the immutable policy baseline. V2 does not rewrite its historical
`contract_ready_not_materialized` state; it binds the later materialization to
the exact qualification report, artifact identity, content hash, row count,
and session bounds.

## Registered state

- one Market-State artifact;
- 287 session rows from 2025-06-23 through 2026-08-12;
- qualification report logical fingerprint
  `20b496eb76ba6597b6937bf2e79924a65491631767e7e1c4ac186281bba04ee3`;
- qualification report SHA-256
  `8f3ec454b2626b3a2feab79e8f38e3ae014c0d853e7698d9266a32dca224b02a`;
- artifact identity fingerprint
  `7d900990ab1a65bf7520658704c83257a96e808f6b996f827f12a80eecda3e4c`;
- artifact content SHA-256
  `a670fb106b559a3b363da8aae0d3c85a8076fd8b0b5952c52537a859e0b1e537`.

Population, feature-matrix, nuisance-control, and outcome-label artifact counts
remain zero. A qualified Market-State panel is not a factor result, Alpha
finding, model input, or Product signal.

## Authority boundary

Campaign Three is registered unread under ADR 0291 and Ledger V4. That
registration does not change this registry's authority: Development outcomes,
Validation, Holdout, canonical writes, cleanup, and deletion remain
unauthorized. The registry permits only exact content-addressed reuse under a
separately governed research stage.
