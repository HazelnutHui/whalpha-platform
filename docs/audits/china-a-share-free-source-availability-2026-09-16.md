# China A-Share Free-Source Availability Audit — 2026-09-16

## Scope

This was a bounded, read-only, zero-persistence availability check for the
initial China A-share daily research foundation. It tested the implemented
BaoStock and AKShare-mediated official-list adapters. It did not retain source
payloads, write `/data`, create stable identities, admit a Universe, construct
returns, open research outcomes, change Product state, publish, or deploy.

## Environment

- workstation project environment;
- BaoStock 0.9.3;
- AKShare 1.18.95;
- implementation contracts on the isolated A-share foundation branch; and
- no provider credentials.

## BaoStock observation

One `query_all_stock` source request for 2026-09-15 completed successfully.
The normalized source census contained:

- 7,378 total security observations;
- 3,458 SSE observations;
- 3,920 SZSE observations;
- zero BSE observations; and
- 7,378 quarantined identities.

This endpoint is an all-security snapshot, not a common-stock Universe. It did
not independently prove board or security form, so no row was promoted from
its code or name. The result confirms source availability and also confirms
that BaoStock alone cannot supply the intended three-exchange common-stock
identity boundary.

## AKShare-mediated official-list observation

Four current-list requests were made on China local date 2026-09-17 through
AKShare interfaces backed by the SSE, SZSE, and BSE list endpoints. The
normalized source census contained:

- 5,565 common-stock observations;
- 1,702 SSE Main Board;
- 618 STAR Market;
- 1,494 SZSE Main Board;
- 1,407 ChiNext; and
- 344 BSE.

All 5,565 rows remained quarantined pending stable-ID assignment. The official
list context can support board and security-form observations, but a current
list cannot be backdated into historical membership and does not by itself
prove the absence of code reuse or a complete lifecycle.

The interface selection is supported by the current
[AKShare stock-data documentation](https://akshare.akfamily.xyz/data/stock/stock.html),
which identifies the SSE, SZSE, and BSE list endpoints and separate SSE/SZSE
delisting endpoints. AKShare is the adapter library; the underlying publisher
must remain visible in every retained source package.

## Important non-comparison

The two observations have different effective dates and populations. The
7,378 BaoStock all-security count and 5,565 current official common-stock count
must not be subtracted or treated as a disagreement census. A valid
cross-source reconciliation requires a common cutoff, retained payloads,
declared population, and exact business keys.

## Lifecycle semantics follow-up

The live lifecycle probe returned 159 SSE rows and 208 SZSE rows. The SSE
interface uses company code plus a field described as a pause-listing date and
contains six duplicated company/date pairs with different listing dates. It
therefore remains issuer-level, pause-or-termination evidence: all 159 rows
carry no listed-security ID. The SZSE route explicitly returned 208 terminated-
listing security-code rows. Both families remain unadjudicated source evidence.

## Temporary normalized reference package

A bounded reference capture wrote only to owner-only custody below `/tmp`
and passed a complete byte/hash/schema/mode/file-set reread. The final plan
covered seven varied anchors across SSE Main, STAR, SZSE Main, ChiNext, and BSE
plus one SSE issuer-lifecycle and one SZSE security-lifecycle subject. Current
official lists covered all seven anchors and both lifecycle subjects. BaoStock
covered all six SSE/SZSE anchors but not BSE.

The first attempted BSE anchor used an obsolete `430xxx` assumption and was
absent from the current official list. The failed package remained an immutable
diagnostic; the plan was corrected to a current official `920xxx` anchor and
rerun. Neither package retained raw upstream bytes or touched `/data`.

## Five-year daily pilot follow-up

Pilot-only adjudication bound the six SSE/SZSE anchors whose official-list and
BaoStock evidence agreed and quarantined the BSE anchor because BaoStock had no
matching instrument observation. The identifiers are deterministic package
join keys, not canonical stable identities.

The linked daily capture covers 2021-09-16 through 2026-09-16 and made 12
source requests: one daily-history and one adjustment-history request for each
bound security. The owner-only package contains:

- 7,255 unadjusted daily bars;
- 7,266 daily source states, including 11 suspended states;
- 259 present-but-unspecified risk-warning states; and
- 28 adjustment observations preserving the provider, forward-adjustment,
  and backward-adjustment factor fields separately.

Seven physical files totaling 8,319,284 bytes passed complete
byte/hash/schema/mode/file-set reread. The quality report keeps raw retention,
canonical identity, calendar reconciliation, adjustment semantics, canonical
Apply, backtest, Product, publication, and deployment authority false.

## Same-scope source-repeat result

A second acquisition used the identical plan, reference package, provider,
six SSE/SZSE securities, and 2021-09-16 through 2026-09-16 interval. The repeat
package and comparison report both passed exact reread. Ignoring only the local
`ingested_at` clock, the result was:

- 7,255 / 7,255 daily bars unchanged;
- 7,266 / 7,266 daily states unchanged;
- 28 / 28 adjustment observations unchanged; and
- zero changed, added, or removed economic rows.

This result qualifies bounded repeat stability only. It does not prove future
provider immutability, missing-session completeness, official calendar or
price-limit correctness, action economics, return semantics, or point-in-time
Universe eligibility.

## Decision

- BaoStock remains the first free raw daily-observation route for SSE/SZSE.
- AKShare-mediated official lists remain an independent current identity and
  board/form source and the initial BSE identity route.
- BSE daily-price history still requires a qualified primary/corroborating
  route; no source is promoted merely because the current list is available.
- The normalized reference/lifecycle and linked daily slices now reread
  exactly, but raw source retention and canonical stable-identity adjudication
  remain separate work.
- Suspensions, risk-warning history, corporate actions, effective-dated rules,
  fees, exact availability clocks, and BSE daily history remain incomplete.
- The bounded source-repeat comparison is zero-delta. The next safe milestone
  is qualification of calendars, price-limit rules, corporate actions, factor
  semantics, fees, and historical Universe decisions. Full-market backfill
  remains closed.

## Verdict

`NORMALIZED_DAILY_PILOT_EXACT_FOUNDATION_INCOMPLETE`
