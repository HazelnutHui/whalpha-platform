# Strong-Leader Pullback SEC Document Content Census

## Boundary

This network-disabled operation parses the complete private SEC source package
and writes one owner-only candidate-localization census. It reads no credential
and cannot write canonical `/data` or a lifecycle fact.

Run from a clean canonical checkout. All inputs and the output custody root
must already exist with owner-only permissions; the exact `census=*` target
must be absent or an identical completed report.

```bash
scripts/admin/census-strong-leader-pullback-sec-document-content.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents/build=20260913-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents \
  --source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content/source=20260913-v1 \
  --source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census/census=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-document-content-census \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Verify all 219 documents parsed, decoding/markup/form counts reconcile, report
and logical hashes are stable, modes are `0700/0400`, and no staging residue
exists. Aggregate marker counts are discovery statistics only. Do not describe
them as matched, absent, or conflicting lifecycle facts.
