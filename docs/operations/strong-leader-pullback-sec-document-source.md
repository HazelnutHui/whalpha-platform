# Strong-Leader Pullback SEC Document Source Custody

## Boundary

This operation downloads only the immutable 219-request plan into owner-only
Dell source custody. It requires the existing protected SEC User-Agent
configuration. It never prints that value and never writes canonical `/data`.

Run only from a clean canonical checkout. The plan and both custody roots must
already exist with owner-only permissions. The output target must be absent,
an exact resumable partial, or an identical completed package.

## First bounded request

Use one document to prove live response behavior and the restart boundary:

```bash
scripts/admin/acquire-strong-leader-pullback-sec-documents.sh \
  --plan /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents/build=20260913-v1 \
  --plan-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-documents \
  --output-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content/source=20260913-v1 \
  --output-custody-root /home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-sec-document-content \
  --maximum-new-documents 1 \
  --execute
```

The expected result is `in_progress` with exactly one completed request inside
the partial package. Inspect only aggregate output, permissions, and hashes;
do not print document or credential content.

## Resume to completion

Repeat the command without `--maximum-new-documents`. Every completed artifact
is formally reread before it is skipped. Progress output contains only request
sequence, batch, byte count, and hashes.

Completion requires 219 formally reread documents, a completed manifest, no
partial/staging residue, exact plan binding, and zero authority counters.
Network failure leaves completed request directories resumable. An unexpected
member, changed document, changed plan, unsafe permission, symlink, or
coexisting final/partial package stops the run.

Do not manually edit, rename, or selectively delete members. Do not interpret
the source package as a security lifecycle or terminal-return dataset. That is
a separate extraction and evidence-admission stage.
