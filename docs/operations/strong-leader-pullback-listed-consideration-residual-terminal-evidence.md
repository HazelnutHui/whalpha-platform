# Strong-Leader Pullback Listed-Consideration Residual Terminal Evidence

This network-disabled operation calculates daily gross reference values only
for the three residual identities.

Run the repository-aware wrapper from a clean canonical checkout with absolute
paths, a fixed UTC evaluation time, and `--execute`:

```bash
scripts/admin/build-strong-leader-pullback-listed-consideration-residual-terminal-evidence.sh \
  --prior-terminal-evidence /absolute/prior/adjudication=... \
  --prior-terminal-evidence-custody-root /absolute/prior \
  --residual-identity /absolute/residual/adjudication=... \
  --residual-identity-custody-root /absolute/residual \
  --consideration /absolute/consideration/adjudication=... \
  --consideration-custody-root /absolute/consideration \
  --cessation /absolute/cessation/adjudication=... \
  --cessation-custody-root /absolute/cessation \
  --payoff-terms /absolute/payoff/adjudication=... \
  --payoff-terms-custody-root /absolute/payoff \
  --canonical-eod-root /data/trading-intelligence-platform \
  --output-root /absolute/output/adjudication=... \
  --output-custody-root /absolute/output \
  --evaluated-at 2026-09-14T07:00:00Z \
  --execute
```

Review all three values, price quality flags, and the prior/residual/cumulative
counts. Exact reruns return `already_present`; different content at the same
target fails closed.

The operation reads but never writes `/data`. It creates no canonical terminal
outcome, strategy label or return, Historical Coverage write, research
admission, Candidate result, publication, deployment, or scheduler change.
