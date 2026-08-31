# Massive Historical Entitlement Probe V1

Contract: `massive-historical-entitlement-probe/1.0`.

The probe makes exactly four serial, zero-retry requests for one exact session:
unadjusted Grouped Daily, active point-in-time Tickers, Splits, and Dividends.
Each line reports only a logical endpoint, safe status, a result count when
available, and optional `Retry-After`.

Every result states zero data writes, no response-body retention, no permission
conclusion and no Historical Pilot authority. An accessible empty result is
distinct from denial. Execution requires the exact acknowledgement emitted by
review mode for the clean implementation revision and session.
