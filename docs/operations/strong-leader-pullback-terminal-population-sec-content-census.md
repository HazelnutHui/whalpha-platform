# Strong-Leader Pullback Terminal-Population SEC Content Census

## Boundary

This zero-network operation parses only the complete corrected-population SEC
source package and creates one owner-only lexical-candidate census. It reads no
credential and cannot write canonical `/data`, lifecycle facts, outcomes, or
research state.

Run from a clean canonical checkout. The authoritative plan and source package
must formally reread, the custody root must already be owner-only, and the
exact `census=*` target must be absent or byte-identical.

```bash
scripts/admin/census-strong-leader-pullback-terminal-population-sec-content.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan/plan=20260914-v2 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan \
  --source /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-content/source=20260914-v2 \
  --source-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-content \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-content-census/census=20260914-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-terminal-population-sec-content-census \
  --evaluated-at YYYY-MM-DDTHH:MM:SSZ \
  --execute
```

Verify that every planned document parsed, all aggregate counts reconcile,
report and logical hashes are stable, modes are `0700/0400`, replay returns the
same report, and no partial or staging residue exists. Marker counts are only a
navigation aid for the later form-aware extraction and adjudication stages.
