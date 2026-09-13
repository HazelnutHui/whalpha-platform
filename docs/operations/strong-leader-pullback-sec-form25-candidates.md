# Strong-Leader Pullback SEC Form 25 Candidate Extraction

## Boundary

This network-disabled operation extracts fixed HTML table fields from the 64
Form 25-NSE documents already in private custody. It does not calculate last-
trade or effective-delisting dates and cannot create a lifecycle fact.

Run from a clean canonical checkout with all input/output roots already
owner-only. The exact `extraction=*` target must be absent or identical.

```bash
scripts/admin/extract-strong-leader-pullback-sec-form25-candidates.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents/build=20260913-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents \
  --source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content/source=20260913-v1 \
  --source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content \
  --content-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census/census=20260913-v1 \
  --content-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form25-candidates/extraction=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form25-candidates \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Verify 64 / 64 extracted documents, 62 instruments, two duplicate-instrument
records, selected-rule and exchange aggregates, report hashes, `0700/0400`
modes, zero residue, and zero authority counters. Do not interpret a selected
rule or notice date as a terminal outcome.
