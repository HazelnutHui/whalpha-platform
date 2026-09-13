# Strong-Leader Pullback SEC Case Coverage Census

## Boundary

This network-disabled operation measures candidate-document coverage across
the frozen 64 lifecycle cases. It does not adjudicate a date, amount, party,
security class, transaction, lifecycle status, or terminal return.

Run from a clean canonical checkout. All source and target roots must already
be owner-only. The exact `census=*` target must be absent or identical.

```bash
scripts/admin/census-strong-leader-pullback-sec-case-coverage.sh \
  --source-sample /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-source-acceptance-sample/build=20260913-v1 \
  --source-sample-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-source-acceptance-sample \
  --form25 /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form25-candidates/extraction=20260913-v1 \
  --form25-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form25-candidates \
  --form15 /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form15-candidates/extraction=20260913-v1 \
  --form15-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-form15-candidates \
  --transaction /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-transaction-candidates/extraction=20260913-v1 \
  --transaction-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-transaction-candidates \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-case-coverage-census/census=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-case-coverage-census \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Verify 64 cases, 219 documents, exact family-case and evidence-profile counts,
eight field candidate-case counts, 512 unsupported complete results, package
hashes, `0700/0400` modes, zero residue, and all zero authority counters.

Do not turn candidate presence into `matched`, candidate absence into event
absence, a referenced exhibit into available content, or a stable-ID join into
security identity. The census measures the next review population only.
