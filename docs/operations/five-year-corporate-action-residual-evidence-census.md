# Five-Year Corporate Action Residual Evidence Census

## Boundary

This operator path rebuilds the ADR 0220 owner-only diagnostic from sealed
local inputs. It makes no network request and writes neither `/data` nor any
canonical, research, analytics, Candidate, website, deployment, or scheduler
state.

Run only from a clean Dell source checkout. Use a new absent `build=*` target;
completed outputs are immutable.

```bash
scripts/dev/run-project-python.sh -m \
  tip_api.services.historical_corporate_action_residual_evidence_census_cli \
  --resolution-shadow /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-resolution-shadow/build=20260913-v2 \
  --resolution-shadow-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-resolution-shadow \
  --unresolved-census /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-unresolved-census/build=20260913-v2 \
  --unresolved-census-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-unresolved-census \
  --lifecycle-shadow /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution/build=five-year-20260912-v1 \
  --lifecycle-shadow-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/inactive-lifecycle-resolution \
  --lifecycle-anchor 2026-07-16 \
  --lifecycle-anchor 2026-09-03 \
  --finra-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/finra-otc-daily-list/five-year-20260910 \
  --finra-range-start 2021-08-11 \
  --finra-range-end 2026-09-09 \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-residual-evidence-census/build=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/corporate-action-residual-evidence-census \
  --evaluated-at 2026-09-13T00:00:00Z \
  --execute
```

Before execution, create only the named custody root as owner mode `0700` if
it does not exist. The CLI refuses a dirty repository, non-owner custody,
duplicate/unsorted lifecycle anchors, overwrite, source drift, malformed
evidence, and any network access.

Successful output is aggregate-only. Review the manifest for source bindings,
candidate-relation states, inactive-source states, FINRA match counts, output
hashes, and all-zero authority counters. Do not use individual rows to assign
identity without a separate governed evidence and Apply decision.
