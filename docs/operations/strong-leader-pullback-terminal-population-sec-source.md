# Strong-Leader Pullback Terminal-Population SEC Source Custody

## Boundary

This operation downloads exactly the three requests frozen by the corrected-
population source plan. It reads the existing protected SEC User-Agent without
printing or retaining it, writes only private source custody outside `/data`,
and performs no content interpretation.

Run from a clean canonical Dell checkout. The plan and both custody roots must
already exist with owner-only permissions.

```bash
scripts/admin/acquire-strong-leader-pullback-terminal-population-sec-source.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan/plan=20260914-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-content/source=20260914-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-content \
  --execute
```

Success requires three formally reread document/artifact pairs, a completed
manifest, exact plan binding, owner-only modes, and no partial residue. Exact
replay must return `already_present` with zero network requests.

Do not inspect document content in the acquisition step or manually edit the
package. Extraction and fact adjudication require a separate contract.
