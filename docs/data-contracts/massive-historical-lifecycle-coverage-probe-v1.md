# Massive Historical Lifecycle Coverage Probe V1

Contract: `massive-historical-lifecycle-coverage-probe/1.0`.

For one exact anchor date, the probe requests `active=false`, `limit=1000`,
sorted All Tickers pages. It follows at most one same-host, same-path `next_url`,
for a two-request maximum with no retry.

The result retains only aggregate counts and a logical fingerprint. Status is
completed, truncated at ceiling, authentication/entitlement/rate/HTTP failure,
unavailable or malformed. It always reports no response retention, zero data
writes, no coverage conclusion and no Historical Pilot authority.
