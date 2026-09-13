# SEC Submissions Payload Census

## Boundary

Run from a clean revision after both SEC source packages and the final Company
Facts payload census pass formal reread. The operation is network-free,
credential-free, and does not write `/data`.

```bash
PYTHONPATH=apps/api/src .venv/bin/python \
  -m tip_api.providers.sec.submissions_payload_census_cli \
  --submissions-package <submissions-root>/snapshot=YYYY-MM-DD \
  --submissions-custody-root <submissions-root> \
  --companyfacts-package <companyfacts-root>/snapshot=YYYY-MM-DD \
  --companyfacts-custody-root <companyfacts-root> \
  --companyfacts-census-root <final-companyfacts-census-root> \
  --output-root <submissions-census-root>/five-year-YYYYMMDD \
  --range-start YYYY-MM-DD \
  --range-end YYYY-MM-DD \
  --workers 8 \
  --execute
```

Eight workers are the Dell default and 16 is the hard ceiling. Company Facts
is reread only to reconstruct the exact target accession/filed-date mapping;
Submissions is then partitioned across workers so each process opens its large
central directory once.

## Stops and interpretation

- Source/census fingerprint drift, archive read/CRC failure, or target-count
  mismatch stops the whole run.
- Invalid independent JSON/container members are quarantined and do not stop
  unrelated member validation.
- Unknown fields are counted. Required/misaligned filing columns, invalid root
  identity, invalid placeholder, and invalid root containers are quarantined.
- Invalid individual accession, filed date, acceptance value, or shard
  reference is counted without inventing a replacement.
- A valid acceptance value must use the SEC archive's exact millisecond UTC
  form. UTC validation is still not a market-session eligibility decision.
- Contract-1.0 output used the wrong compact/local-time assumption; retain it
  only as superseded diagnostic evidence and run contract 1.1 into a distinct
  owner-only output root.

After sealing, formally reread the report. Any missing/conflicting target set
must become an explicit normalization quarantine or a bounded source-recovery
task; it cannot be filled with a current value or silently omitted.
