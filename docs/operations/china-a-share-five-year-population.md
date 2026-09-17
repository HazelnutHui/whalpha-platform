# China A-share Five-Year Population Freeze

This operation freezes the exact SSE/SZSE acquisition population before bulk
five-year source capture. It reads an exactly retained identity/lifecycle
package, performs one BaoStock security-basic census, and writes a new
immutable owner-only package outside canonical `/data`.

```bash
scripts/admin/capture-china-ashare-five-year-population.sh \
  --identity-lifecycle-package /absolute/identity-lifecycle-package \
  --custody-root /absolute/private/population-custody \
  --interval-start 2021-09-16 \
  --interval-end 2026-09-16
```

The operation is idempotent by logical package identity. It retains the five
official raw artifacts, the provider census, every disposition, conflict
reasons, the report, and the manifest. It rejects unsafe paths, duplicate
provider IDs, changed source bytes, unexpected package files, and fingerprint
differences. It grants no canonical Apply, research, Product, publication, or
deployment authority.
