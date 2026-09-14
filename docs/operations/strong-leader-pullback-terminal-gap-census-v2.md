# Strong-Leader Pullback Terminal Gap Census V2

## Boundary

This command combines only formally retained local evidence. It performs no
network request, writes nothing to `/data`, and does not calculate returns,
admit research, update Candidates, publish, deploy, or mutate a scheduler.

Run from a clean checkout. The output custody root must already be an owner-
only mode-`0700` directory.

```bash
scripts/admin/build-strong-leader-pullback-terminal-gap-census-v2.sh \
  --boundary-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-boundary-census/census=<boundary-id> \
  --boundary-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-boundary-census \
  --prior-gap-census /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census/census=20260914-v1 \
  --prior-gap-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census \
  --source-sample /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-source-acceptance-sample/build=20260913-v1 \
  --source-sample-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-source-acceptance-sample \
  --lifecycle-shadow /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution/build=five-year-20260912-v1 \
  --lifecycle-shadow-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution \
  --lifecycle-anchor 2026-07-16 \
  --lifecycle-anchor 2026-09-03 \
  --payoff-terms /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms/adjudication=20260914-v1 \
  --payoff-terms-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-payoff-terms \
  --fixed-cash /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-fixed-cash-terminal-evidence/adjudication=20260914-v1 \
  --fixed-cash-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-fixed-cash-terminal-evidence \
  --listed-terminal /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-terminal-evidence/adjudication=20260914-v1 \
  --listed-terminal-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-terminal-evidence \
  --residual-terminal /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-residual-terminal-evidence/adjudication=20260914-v1 \
  --residual-terminal-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-residual-terminal-evidence \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v2/census=<bounded-id> \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-gap-census-v2 \
  --evaluated-at <UTC-ISO-8601> \
  --execute
```

The result is a worklist, not a performance report. Use its corrected path
counts and priority order only after formal reread.
