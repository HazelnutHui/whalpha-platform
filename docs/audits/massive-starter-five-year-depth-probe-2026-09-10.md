# Massive Starter Five-Year Depth Probe — 2026-09-10

## Outcome

Three exact-date, non-retaining entitlement probes tested the current Stocks
Starter credential through the existing four-request contract. Twenty-four
seconds of enforced serial pacing separated requests. No response body was
retained and no data or Production write occurred.

| Session | Grouped Daily, unadjusted | PIT active tickers | Splits | Dividends | Fingerprint |
| --- | --- | --- | --- | --- | --- |
| 2021-09-09 | entitlement denied | accessible | accessible | accessible | `4b773687b925ecaabc2e24fb2e8cab804e98a4301997c7615f204862232277c2` |
| 2021-09-10 | entitlement denied | accessible | accessible | accessible | `a369790724ac4a5a5de9a550779e066460639854c8688950487c48af3290931f` |
| 2022-09-09 | accessible, 11,063 results | accessible | accessible | accessible | `85b0b12f3feca4816f622f8111ee1e8adaf9646349d5a9e8ece815ddc5c14d47` |

The probe establishes endpoint behavior only. It does not establish an exact
REST cutoff, complete pagination, source permission, historical completeness,
or data quality. Repeating the denied request cannot close the five-year price
gap.

## Route decision

Massive's current official Stocks pricing describes Starter as five years of
history. The official Day Aggregates Flat Files documentation specifically
lists five-year Starter access, and the Flat Files Quickstart recommends that
route for bulk historical downloads. Flat Files require a separate S3 Access
Key and Secret Key from the Massive dashboard; the existing REST API-key
boundary does not contain those credentials.

Therefore:

- Day Aggregates Flat Files become the preferred five-year bulk price source;
- Grouped Daily REST remains the daily/current route, a bounded fallback for
  dates it actually authorizes, and a cross-source reconciliation input;
- point-in-time Tickers remains the historical Identity route subject to full
  pagination and custody; and
- split/dividend REST remains source observation, never sole canonical action
  or lifecycle authority.

The adapter must preserve the compressed source artifact or its exact hash,
source key, observed time, row count, schema, and unadjusted/adjusted semantics.
It must normalize through the existing stable-ID and EOD contracts rather than
creating a parallel price database.

Official references:

- <https://massive.com/pricing?product=stocks>
- <https://massive.com/docs/flat-files/stocks/day-aggregates>
- <https://massive.com/docs/flat-files/quickstart>
- <https://massive.com/docs/rest/stocks/aggregates/daily-market-summary>

## Non-conclusions

No S3 credential was requested, read, or inferred during this probe. No Flat
File object was listed or downloaded. The five-year EOD family remains
incomplete, and REST denial is not evidence that the documented Flat File
entitlement is unavailable.

