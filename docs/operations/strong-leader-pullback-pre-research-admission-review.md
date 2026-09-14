# Strong-Leader Pullback Pre-Research Admission Review

Run from a clean commit. The command rereads existing canonical and private
evidence, recomputes the split negative-space diagnostic, and writes only one
immutable owner-only review outside `/data`.

```bash
scripts/admin/review-strong-leader-pullback-pre-research-admission.sh \
  --development-census /tmp/whalpha-strong-leader-pullback-development-census-20260910T032422Z-1f6447110142 \
  --prior-admission /tmp/whalpha-strong-leader-pullback-development-admission-20260910T040933Z-bd358defe390 \
  --blocker-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-evidence-blocker-census/build=20260913-v1 \
  --blocker-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-evidence-blocker-census \
  --terminal-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v4/census=20260914-v4 \
  --terminal-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v4 \
  --data-root /data/trading-intelligence-platform \
  --canonical-action-publication /data/trading-intelligence-platform/market-data/canonical-corporate-actions/schema_version=1/action_scope=split/coverage_id=76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218 \
  --adjustment-publication /data/trading-intelligence-platform/market-data/adjustment-ledger/schema_version=1/methodology_version=canonical-split-ratio-to-basis-v1/basis_session=2026-09-04/coverage_id=7e08b8a8ee364cf215c1459645f76240368b50cc3d2cb4bc77db86d3ca7c3c2a \
  --eod-evidence /data/trading-intelligence-platform/market-data/historical-coverage-evidence/schema_version=1/family=eod_price_bar/evidence_id=923f27a8fa4e85c6d20b5c8ac0804f17dbab7437b350f02d54fea2ed5293aeb1/manifest.json \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-pre-research-admission-review/review=<bounded-id> \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-pre-research-admission-review \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

The expected current result is `rejected_data_blocked`. Exact replay must
return `already_present`; modes must be `0700/0400`; no partial, symlink,
Historical Coverage, outcome, `/data`, or Production residue may be created.
