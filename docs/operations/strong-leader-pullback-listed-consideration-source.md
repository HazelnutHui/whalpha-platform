# Strong-Leader Pullback Listed-Consideration Source Custody

## Boundary

This operation downloads only the 12 exact 424B3 files frozen by the source
plan into owner-only Dell custody. It requires the existing protected SEC
User-Agent configuration, never prints that value, and never writes `/data`.

Run only from a clean canonical checkout. The plan and custody roots must
already exist with owner-only permissions. The target may be absent, an exact
resumable partial, or an identical completed package.

## One-document live probe

Prove response and restart behavior with one bounded document:

```bash
scripts/admin/acquire-strong-leader-pullback-listed-consideration-source.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-source-plan/plan=20260914-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-listed-consideration-source-plan \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-listed-consideration-document/source=20260914-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-listed-consideration-document \
  --maximum-new-documents 1 \
  --execute
```

The expected result is `in_progress` with one formally bound request in the
partial package. Progress output contains only sequence, byte count, and hash;
it contains no source content or credential material.

## Resume and completion

Repeat the same command without `--maximum-new-documents`. Completed request
directories are reread and rehashed before they are skipped. Completion
requires all 12 documents, one exact manifest, no partial or staging residue,
owner-only modes, exact plan binding, and zero authority counters.

An interrupted per-request staging directory is discarded only after its name,
owner, mode, location, and sequence are validated. Unknown content, a changed
document, a response metadata mismatch, an unsafe path, or coexisting final
and partial packages stop the operation.

Do not manually edit, selectively delete, or interpret package members. A
separate adjudication must prove transaction, target security, consideration
class, and exchange ratio before any candidate stable ID can be assigned.
