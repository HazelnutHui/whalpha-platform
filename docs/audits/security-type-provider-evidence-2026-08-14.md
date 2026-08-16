# Provider Security-Type Evidence Attempt: 2026-08-14

- Operation time: 2026-08-16 UTC
- Provider: Massive Stocks Basic
- Result: quality-gate failure; no evidence partition published

## Network And Reconciliation

- Ticker Types requests: 1
- All Tickers requests: 14
- Total requests: 15
- Retries: 0
- Catalog records received: 25
- All Tickers raw records: 13,110
- Uniquely mapped canonical evidence: 9,937
- Exact duplicates: 0
- Ambiguous: 4
- Canonically unjoined: 3,169
- Malformed: 0

The categories reconcile exactly: 9,937 + 0 + 4 + 3,169 = 13,110. Stable identifier collision gate did not fail. The mapped business-key duplicate gate was nonzero, but the first safe summary did not retain its exact count; it is therefore recorded as unknown/nonzero rather than guessed.

## Gate Failure

The run reported an identity join ratio of 0.757971 because the implementation divided canonical mappings by all raw records. That incorrectly treated expected-exclusion records already present in Provider Identity, but intentionally lacking canonical IDs, as identity misses. The implementation now measures linkage to the accepted identity snapshot separately from canonical evidence creation.

Four ambiguous mappings and nonzero mapped business-key conflicts remain independent hard failures. Raw payloads were not saved, so their provider rows cannot be reconstructed offline. A second request sequence was not attempted.

## Unavailable Outputs

No catalog or instrument evidence partition was published. Therefore provider-code distribution, security-form reclassification, legacy-pool deterministic exclusions, updated quarantine counts, and updated Core/Broad candidate counts are unavailable for this attempt. Phase A counts remain historical context only and were not presented as Phase B1 results.

VCX, AKAN, VXT, and AZ received no new persisted provider evidence in this attempt. Existing authoritative Phase A decisions remain unchanged.

## Production Effect

Existing Instrument Master, Provider Identity, Ticker Resolver, EOD, and Dashboard snapshot data were unchanged. Provisional-governance UI and snapshot-contract changes are implemented and tested in source, but production snapshot generation and OCI deployment were correctly blocked.
