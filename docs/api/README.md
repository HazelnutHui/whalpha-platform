# API Documentation

## Dashboard contract 2.1

Each ordinary Universe view may carry a `funnel` array. Contract 2.1 requires exactly ten ordered records per Universe with `universe_id`, `stage_index`, `stage_id`, `display_label`, `input_count`, `excluded_count`, `remaining_count`, `source_revision`, `source_session`, and `source_fingerprint`. Each stage and adjacent pair must close arithmetically. Contract 2.0 remains readable with no formal Funnel; clients must not reconstruct one from summary fields.

Private Dashboard market routes consume the completed Dashboard Universe Activation V1 reader. All Universe-dependent endpoints accept the same allowlisted stable ID and return the actual selected metadata.

This directory records API contracts and exposure boundaries.

- [Private EOD Market Data V1](private-eod-market-data-v1.md)
- [Private Market Summary V1](private-market-summary-v1.md)

Frontend consumer documentation: [Market Dashboard V1](../frontend/market-dashboard-v1.md).
