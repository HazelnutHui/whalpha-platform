# Strong-Leader Pullback Listed-Consideration Source Plan

This network-disabled operation freezes 12 transaction-registration documents
for later consideration-security identity adjudication.

Run the repository-aware wrapper with absolute inputs, owner-only output
custody, a fixed UTC evaluation time, and `--execute`:

```bash
scripts/admin/plan-strong-leader-pullback-listed-consideration-source.sh \
  --payoff-terms /absolute/payoff-terms/adjudication=... \
  --payoff-terms-custody-root /absolute/payoff-terms \
  --party-relations /absolute/party-relations/adjudication=... \
  --party-relations-custody-root /absolute/party-relations \
  --cessation /absolute/cessation/adjudication=... \
  --cessation-custody-root /absolute/cessation \
  --submissions-package-root /absolute/submissions/snapshot=... \
  --submissions-custody-root /absolute/submissions \
  --canonical-eod-root /data/trading-intelligence-platform \
  --output-root /absolute/source-plans/plan=... \
  --output-custody-root /absolute/source-plans \
  --evaluated-at 2026-09-14T20:00:00Z \
  --execute
```

The repository must be clean. Exact reruns return `already_present`; a
differing report at the same target fails closed.

The command makes no network request and does not retrieve the 424B3 files,
assign consideration-security identity, value stock consideration, write
`/data` or Historical Coverage, admit research, publish, deploy, or change a
scheduler.
