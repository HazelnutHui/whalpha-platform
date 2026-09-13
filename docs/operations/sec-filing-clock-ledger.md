# SEC Filing-Clock Ledger

## Boundary

Build only from clean code after formal reread of the final Company Facts and
Submissions source packages and payload censuses. The operation is
network-free, credential-free, and must not write `/data` while another
canonical writer is active.

The target parent is an owner-only historical-source state root. The exact
package path must not already exist; a partial sibling causes a stop rather
than automatic deletion.

```bash
PYTHONPATH=apps/api/src .venv/bin/python \
  -m tip_api.providers.sec.filing_clock_ledger_cli \
  --submissions-package <submissions-package> \
  --submissions-custody-root <submissions-root> \
  --submissions-census-root <final-submissions-census-root> \
  --companyfacts-package <companyfacts-package> \
  --companyfacts-custody-root <companyfacts-root> \
  --companyfacts-census-root <final-companyfacts-census-root> \
  --output-package <filing-clock-root>/build=<id> \
  --range-start YYYY-MM-DD \
  --range-end YYYY-MM-DD \
  --workers 8 \
  --execute
```

## Required stops

- dirty implementation revision;
- source/census binding drift;
- target or discrepancy counts that do not reproduce the sealed census;
- unsafe path, ownership, mode, symlink, existing target, or partial residue;
- invalid SEC time, XNYS mapping failure, duplicate output key, schema drift,
  row/fingerprint/hash mismatch, or atomic publication failure.

Missing Submissions evidence is a row-level quarantine, not a whole-build
failure. Acceptance and filed-date disagreements are retained, counted, and
handled by the frozen conservative rule; no first-row selection is allowed.

After publication, run the formal reader and record package identity, counts,
residuals, tests, and authority boundary in a dated audit and current status.
