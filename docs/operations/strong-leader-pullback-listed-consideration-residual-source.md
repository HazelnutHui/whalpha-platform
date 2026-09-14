# Strong-Leader Pullback Listed-Consideration Residual Source Custody

This operation acquires the single Fifth Third 424B3 frozen by the residual
source plan. It uses the protected SEC User-Agent configuration without
printing or retaining it.

Run the repository-aware wrapper from a clean checkout with absolute owner-only
paths and `--execute`:

```bash
scripts/admin/acquire-strong-leader-pullback-listed-consideration-residual-source.sh \
  --plan /absolute/residual/plan=... \
  --plan-custody-root /absolute/residual \
  --output-root /absolute/source/source=... \
  --output-custody-root /absolute/source \
  --execute
```

An interrupted per-document staging directory is removed before retry. A
completed artifact is formally reread before resume, and a fully completed
partial package is adopted without a new request. Exact completed reruns return
`already_present` with zero network requests.

The command does not interpret the document, assign identity, calculate a
terminal value or strategy result, write `/data` or Historical Coverage, admit
research, publish, deploy, or change a scheduler.
