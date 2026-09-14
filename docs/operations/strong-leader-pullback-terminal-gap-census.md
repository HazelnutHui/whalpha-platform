# Strong-Leader Pullback Terminal Gap Census

This operation measures the remaining terminal-evidence gaps for the fixed
first-strategy lifecycle population. It makes no network request and does not
read credentials or write `/data`.

Run the repository-aware wrapper from a clean canonical checkout with absolute
paths, a fixed UTC evaluation time, and `--execute`:

```bash
scripts/admin/build-strong-leader-pullback-terminal-gap-census.sh \
  --blocker-census /absolute/blocker/build=... \
  --blocker-census-custody-root /absolute/blocker \
  --source-sample /absolute/sample/build=... \
  --source-sample-custody-root /absolute/sample \
  --payoff-terms /absolute/payoff/adjudication=... \
  --payoff-terms-custody-root /absolute/payoff \
  --fixed-cash /absolute/fixed/adjudication=... \
  --fixed-cash-custody-root /absolute/fixed \
  --listed-terminal /absolute/listed/adjudication=... \
  --listed-terminal-custody-root /absolute/listed \
  --residual-terminal /absolute/residual/adjudication=... \
  --residual-terminal-custody-root /absolute/residual \
  --output-root /absolute/output/census=... \
  --output-custody-root /absolute/output \
  --evaluated-at 2026-09-14T07:00:00Z \
  --execute
```

Review the complete population, documented/remaining counts, state impacts,
path impacts, priority order, source bindings, and every zero-authority field.
Exact reruns return `already_present`; different content at the same target
fails closed.

The report is not a development admission. It creates no lifecycle fact,
terminal outcome, strategy label, return, metric, canonical data, Historical
Coverage, Candidate result, publication, deployment, or scheduler change.
