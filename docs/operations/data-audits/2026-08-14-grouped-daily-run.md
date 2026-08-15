# 2026-08-14 Grouped Daily Run Report

## Operation

- Operation type: canonical Grouped Daily EOD publication
- Session date: 2026-08-14
- Endpoint path: `/v2/aggs/grouped/locale/us/market/stocks/2026-08-14`
- Adjusted: false
- Request count: 1
- Retry count: 0
- Started at: 2026-08-15T22:41:36Z
- Completed at: 2026-08-15T22:41:44Z
- Identity as-of date: 2026-08-14
- Identity snapshot fingerprint: `cc6b0f802196480339fc633645cedc62656047e70d8d7a86974ddcc15bc88dd0`
- Publish result: published

This report contains no credential, authorization header, raw response, or provider request payload.

## Quality Result

- raw results: 12,424
- unique raw tickers: 12,422
- exact duplicate tickers / records: 0 / 0
- conflicting duplicate tickers / records: 2 / 4
- conflicting duplicate ratio: 0.03219575016097875%
- resolved eligible: 9,916
- unresolved eligible: 982
- expected exclusions: 1,424
- ambiguous / rejected / missing identity: 0 / 89 / 13
- eligible identity denominator: 10,911
- resolved identity coverage: 90.88076253322335%
- numeric classified / valid: 12,420 / 12,420
- total and field-level numeric failures: 0
- required missing: 0
- optional VWAP / trade-count missing: 3 / 3
- fractional-volume records: 11,216
- nonpositive price / OHLC inconsistency / negative volume: 0 / 0 / 0
- zero-volume records: 3
- timestamp mismatch: 0
- canonical validation failures: 0
- canonical bars: 9,912
- count reconciliation: passed
- all hard quality gates: passed

The four conflicting observations were isolated by the accepted low-ratio duplicate policy. They did not enter canonical bars and were retained as a session quality warning. Other warnings record optional missing values, fractional and zero volume, expected exclusions, and unresolved eligible identities.

## Publication Verification

- Schema: EOD Price Bar physical schema version 1, verified by Parquet reread
- Record count: 9,912
- Content SHA-256: `f08033f26d920cc32ce4c12417521a57f45835c316994aae66c1a7da2a8501d2`
- Identity reference: verified against the accepted 2026-08-14 logical snapshot
- Completion status: completed
- Staging residue: none
- Raw payload persistence: none
