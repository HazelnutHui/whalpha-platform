# SEC Company Facts Payload Census

## Boundary

Run this stage from a clean repository revision after the source package has
passed formal reread. It uses no network or credentials and does not write
`/data`. It reads the compressed package in place and writes one compact
owner-only census to a separate historical-source evidence root.

Create and verify the output root as mode `0700`, then run:

```bash
PYTHONPATH=apps/api/src .venv/bin/python \
  -m tip_api.providers.sec.companyfacts_payload_census_cli \
  --source-package <companyfacts-root>/snapshot=YYYY-MM-DD \
  --source-custody-root <companyfacts-root> \
  --output-root <companyfacts-census-root>/five-year-YYYYMMDD \
  --range-start YYYY-MM-DD \
  --range-end YYYY-MM-DD \
  --workers 8 \
  --execute
```

The worker count must remain between 1 and 16. Eight is the default Dell
profile. Work is divided into deterministic 128-member batches. The CLI
requires a clean source revision and reports only structural counts, hashes,
paths, and zero-authority fields.

## Interpretation and stops

- Archive/read/CRC failure stops the run because complete coverage is
  unproven.
- Isolated invalid JSON or malformed issuer structures are retained in the
  quarantine list; valid independent members continue.
- Empty `{}` and filename-bound empty-`facts` placeholders are reported
  separately and are not silently dropped or mislabeled as corruption.
- Filed dates are date-level diagnostics only. Do not use them for same-day
  signal eligibility.
- A successful census does not authorize fact normalization, CIK-to-security
  resolution, canonical Apply, research evaluation, Product publication,
  deployment, or scheduler changes.

After completion, formally reread the sealed report, record its physical and
logical fingerprints, and compare measured schemas with the proposed
normalization contract. The next source dependency is accession-level SEC
submissions acceptance time, not a current-ratio shortcut.
