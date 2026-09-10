# Historical Corporate Action Source Package V1

Contracts: `historical-corporate-action-source-package/1.0` and backward-
compatible `historical-corporate-action-source-package/1.1`.

This contract governs temporary source custody for one Massive split or
dividend observation range. It is neither canonical Corporate Action nor the
Adjustment Ledger.

## Scope

One package has exactly one kind and date field:

| Kind | Endpoint | Inclusive provider-date filter |
| --- | --- | --- |
| `split` | `/stocks/v1/splits` | `execution_date` |
| `dividend` | `/stocks/v1/dividends` | `ex_dividend_date` |

The request uses a 5,000-row limit and ascending date sort. Valid provider
dates must remain inside the requested range and nondecreasing across the
complete package. Missing or malformed dates are counted for later quarantine;
they are not coerced into a different date.

## Physical custody

- Acquisition uses an exact `kind=START_END` target beneath an owner-only
  `/tmp` parent.
- A completed package may be copied byte-for-byte into a separately approved,
  owner-only persistent source directory and formally reread there. The caller
  must supply the exact direct parent; the reader rejects broader, nested,
  symlinked, non-owner, or non-0700 custody roots. Persistent private reread is
  recovery custody only and does not make the package canonical.
- Contract 1.0 retains its original 16 immutable pages, 80,000 rows, and
  15-second request interval.
- Contract 1.1 permits up to 80 immutable pages and 400,000 rows for the exact
  five-year range. It retains the 32 MiB per-page and 512 MiB per-package
  limits.
- Contract 1.1 records one exact serial interval from 0.25 through 15 seconds
  in every checkpoint and the completed manifest. Resume with a different
  interval fails closed. Both versions retain zero automatic retries.
- Atomic checkpoint after every page and complete formal reread before resume
  or success.
- Exact request chain, page sequence, file set, mode, byte size, physical hash,
  and logical fingerprint.
- One exact page written immediately before checkpoint failure may be adopted
  only when its derived request binding is the expected next request.

Provider `request_id`, pagination URLs, credentials, and Authorization material
are never retained. Credential-free cursor parameters and request hashes remain
inside the owner-only package solely for recovery and chain verification.

## Evidence semantics

Source fields are retained without assigning canonical meaning. The manifest
records known-field presence, unexpected-field counts, missing/malformed
effective-date counts, duplicate nonempty provider action IDs, and natural
pagination completion. An empty completed package is valid evidence that the
specific request returned zero rows; it is not by itself a general no-action
claim.

Identity resolution is explicitly `not_attempted`. Downstream mapping must use
the exact event-date Identity view and stable `instrument_id`; ticker is only a
provider locator. Zero or multiple matches remain quarantined.

The provider does not supply a defensible source-availability timestamp for
these rows. Source observation time proves only when WH Alpha observed a page.
It cannot backdate event knowledge into a historical signal.

Provider `historical_adjustment_factor` and
`split_adjusted_cash_amount` remain source evidence. They do not authorize an
Adjustment Ledger write until event ordering, basis, corrections, and
independent Decimal math reconcile.

## Explicit zero-authority fields

Every completed manifest records zero:

- canonical Corporate Action writes;
- Adjustment Ledger writes;
- analytics executions;
- publications;
- deployments; and
- scheduler changes.

The package remains `source_observation_only` and cannot satisfy Historical
Coverage or research readiness.

The larger 1.1 ceiling is not a completeness claim. Natural pagination must
still end below every bound, and a ceiling hit requires a separate review.
