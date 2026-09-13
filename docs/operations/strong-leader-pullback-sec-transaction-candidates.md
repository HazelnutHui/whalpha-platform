# Strong-Leader Pullback SEC Transaction Candidate Extraction

## Boundary

This network-disabled operation creates a form-aware candidate index from the
89 retained 8-K, tender, proxy-material, and foreign-report primary documents.
It does not download referenced exhibits, resolve listed-security identity, or
create transaction, lifecycle, terminal-return, or research facts.

Run from a clean canonical checkout with owner-only input/output roots. The
exact `extraction=*` target must be absent or identical.

```bash
scripts/admin/extract-strong-leader-pullback-sec-transaction-candidates.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents/build=20260913-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents \
  --source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content/source=20260913-v1 \
  --source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content \
  --content-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census/census=20260913-v1 \
  --content-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-transaction-candidates/extraction=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-transaction-candidates \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Verify 89 documents, 63 stable-ID locators, exact form and structure-state
counts, field document/occurrence counts, one referenced-only completion
exhibit, report hashes, `0700/0400` modes, zero residue, and all zero authority
counters.

Do not treat an Item 2.01 heading, merger word, effective-time phrase, tender
status, date token, CIK, or source-plan stable ID as a completed security-level
lifecycle fact. Absence from a primary document is not event absence.
