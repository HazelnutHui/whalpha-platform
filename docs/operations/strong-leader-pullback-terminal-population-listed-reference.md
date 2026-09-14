# Strong-Leader Pullback Terminal-Population Listed Reference

## Boundary

This zero-network operation formally rereads local SCS, SEC Submissions,
historical Instrument Master, and canonical EOD evidence. It assigns HNI only
through the strict stable-security gate and calculates three daily references;
it does not write `/data` or create a strategy outcome.

```bash
scripts/admin/adjudicate-strong-leader-pullback-terminal-population-listed-reference.sh \
  --payoff-policy /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-payoff-policy/adjudication=20260914-v1 \
  --payoff-policy-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-payoff-policy \
  --core-adjudication /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-core-adjudication/adjudication=20260914-v1 \
  --core-adjudication-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-core-adjudication \
  --cessation /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-trading-cessation-adjudication/adjudication=20260914-v1 \
  --cessation-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-trading-cessation-adjudication \
  --submissions-package /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions/snapshot=2026-09-10 \
  --submissions-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/sec-submissions \
  --canonical-eod-root /data/trading-intelligence-platform \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-listed-reference/adjudication=<bounded-id> \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-listed-reference \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Run from a clean commit with an existing owner-only output custody root. Verify
the stable ID, HNI close, three alternative values, mixed primary value,
upstream hashes, exact replay, `0700/0400` modes, and absence of symlink or
partial residue before recording the result.
