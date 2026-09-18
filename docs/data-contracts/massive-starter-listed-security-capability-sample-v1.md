# Massive Starter Listed-Security Capability Sample V1

Contract: `quant-research-massive-starter-capability-sample/1.0`.

This contract binds three deterministic cases selected without outcomes from
ADR 0308's listed-security applicability denominator: one single-common case,
one stable instrument observed under two tickers, and one member of a
same-session multi-common CIK group. Selection is the lexicographically first
provider-locatable stable ID in each class, not a company-name, return, or
coverage-convenience sample.

The exact request budget is ten serial Massive Starter calls with zero retry:
three current Ticker Details, four ticker-and-date filtered All Tickers calls,
and three Composite-FIGI Ticker Events calls. No response may exceed 1 MiB.
The first authentication, entitlement, rate-limit, transport, or malformed
response stops the run. The plan cannot expand after execution.

Successful bodies are sanitized for credential-bearing fields and URLs before
they enter owner-only custody. The credential value is neither retained nor
hashed. Plan, result, sanitized raw responses, response-schema paths, and
verification are written atomically and exactly reread.

An accessible response is not historical authority. Historical
instrument/CIK, form, or alias evidence remains blocked or corroboration-only
unless the payload proves the complete stable relation, effective interval,
revision semantics, and source availability by the historical signal cutoff.
Provider reference data never proves issuer structure. All projection,
factor, outcome, Validation, Holdout, canonical, and Product authority remains
false.
