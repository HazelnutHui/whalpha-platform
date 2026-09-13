# Strong-Leader Pullback SEC Form 15 Candidate Extraction

## Boundary

This network-disabled operation extracts bounded field candidates from the 66
Form 15 documents already in private custody. It does not infer a last-trade,
delisting, deregistration-effective, reporting-suspension-effective, or
terminal date and cannot create a lifecycle fact.

Run from a clean canonical checkout with all input/output roots already
owner-only. The exact `extraction=*` target must be absent or identical.

```bash
scripts/admin/extract-strong-leader-pullback-sec-form15-candidates.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents/build=20260913-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents \
  --source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content/source=20260913-v1 \
  --source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content \
  --content-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census/census=20260913-v1 \
  --content-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form15-candidates/extraction=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form15-candidates \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Verify 66 / 66 documents, 62 instruments, form and field-state aggregates,
selected-rule aggregates, report hashes, `0700/0400` modes, zero residue, and
zero authority counters. Preserve multiple candidates and unsupported
templates. Do not interpret a certification date, rule selection, or Form 15
filing as the effective termination of trading, registration, or reporting.
