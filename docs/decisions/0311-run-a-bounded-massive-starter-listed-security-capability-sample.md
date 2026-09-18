# ADR 0311: Run a Bounded Massive Starter Listed-Security Capability Sample

## Status

Accepted; all historical admission lanes remain closed

## Date

2026-09-18

## Context

ADR 0310 classified Massive Starter as useful but insufficient because the
repository had no exact, current-subscription sample against the ADR 0308
cash-quality applicability population. A small live sample can distinguish
endpoint access from historical semantics without expanding to another
population or reading outcomes.

## Decision

Adopt `quant-research-massive-starter-capability-sample/1.0` with exactly three
cases selected from the ADR 0308 denominator by stable-ID lexical order among
provider-locatable candidates:

| Kind | Stable instrument | Local denominator evidence |
| --- | --- | --- |
| Single common | `0009f17a-9e07-50b4-80b0-c99dde042549` | AGL, CIK `0001831097` |
| Ticker change | `013f4751-d9cf-5e20-9ad2-a33b4e8f4f19` | DRQ then INVX, CIK `0001042893` |
| Multi-common | `053b0fba-1c72-5171-b97f-5c4596010895` | URBN in the same CIK/session group as stable instrument `1fa2428f-2f8a-5b64-96ca-c4587c9642e9` / BATRK |

The eligible local candidate counts were 3,253 single-ticker single-common
stable IDs, 223 ticker-change stable IDs, and 195 provider-locatable
multi-common groups. These counts and lexical selection use no outcome,
Validation, or Holdout data.

Plan fingerprint
`7a5e00b4414eaf6baf3d4513e094a6e53fe0434470dd8a0e6389fcac25519572`
authorizes ten serial calls, zero retries, a 0.25-second interval, a 1 MiB
per-response ceiling, and immediate stop on the first failed call:

- three current `/v3/reference/tickers/{ticker}` details;
- four `/v3/reference/tickers` requests filtered by exact ticker and date; and
- three `/vX/reference/tickers/{composite_figi}/events` requests.

No endpoint, identifier, date, or request may be added after registration.

## Result

All ten requests completed. There was no authentication, entitlement,
rate-limit, transport, or response-size failure. Sanitized owner-only custody
exactly rereads at:

`massive-starter-capability-sample-v1/verification=4c957cebedc5055c9694dd2bafa42f0e9c793559ec6bb9f1026975d68c7f0475`

The authoritative result fingerprint is
`1bb97bf204c228639c92fbfec80bab29e545fd443973f6bd84942c7717f4bea9`.
It retains 13 evidence files totaling 27,286 bytes before the verification
file. Directories are mode 0700 and files mode 0600. The credential value was
neither retained nor hashed.

Observed semantics:

- all three current details returned ticker, CIK, `CS`, Composite FIGI, Share
  Class FIGI, exchange, active state, and a list date;
- AGL, DRQ, and URBN dated rows returned the expected CIK, FIGIs, and `CS`;
- the INVX 2024-09-09 dated row returned the same Composite and Share Class
  FIGIs and `CS`, but omitted CIK;
- dated rows exposed `last_updated_utc` values from 2024-12-03, later than the
  requested historical dates; these are retrospective record-update fields,
  not proof that the facts were available at the earlier signal open; and
- Ticker Events returned one event for each case. The DRQ/INVX stable FIGI
  returned an INVX ticker-change event effective 2024-09-09. Events expose the
  new ticker and effective date but not a complete prior alias interval,
  publication/availability clock, cancellation chain, or coverage guarantee.

## Disposition

| Lane | Disposition | Reason |
| --- | --- | --- |
| Effective-dated instrument↔CIK | Blocked | One requested dated alias omitted CIK; all responses were observed now and provide no historical signal-open availability proof. |
| Effective-dated security form | Corroboration only | All four dated rows returned `CS`, but the endpoint does not supply a revision-aware historical form ledger or historical availability clock. |
| Listing interval and aliases | Corroboration only | Stable FIGIs and the 2024-09-09 ticker event corroborate DRQ→INVX continuity, but do not establish a complete listing/alias interval or revision/availability history. |
| Issuer/security structure | Blocked | CIK, FIGI, `CS`, current details, and ticker events are not issuer operating-structure evidence. |
| Multi-common policy | Still quarantine | The local same-session group remains evidence that one CIK association can reach multiple securities; one per-ticker provider response cannot choose a security or repair the relationship. |

Therefore Massive Starter endpoint access is not the blocker. Historical
knowledge time and semantic completeness are. No historical lane is admitted,
no security projection is created, and ADR 0308 remains at zero applicable
rows.

Two earlier immutable packages from the same ten retained responses record
intermediate parser dispositions. They are not authoritative; the verification
path and result fingerprint above bind the corrected nested Ticker Events
schema and independent stable-FIGI alias evaluation. No provider request was
repeated during those offline corrections.

No paid upgrade, broader population, canonical write, factor, outcome,
Validation, Holdout, Candidate, Product, or Production action is authorized.
