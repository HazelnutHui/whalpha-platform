# Market Session Calendar and Freshness

## Scope

The Market Session Calendar determines which XNYS cash-equity session is expected to be complete at a timezone-aware instant. It does not fetch market data and does not decide whether a provider publication succeeded.

## Boundary

`ExchangeCalendar` wraps the offline `exchange-calendars` XNYS schedule and exposes:

- `is_session(date)`
- `previous_session(date)`
- `latest_completed_session(as_of_datetime)`
- `session_lag(current_session, expected_latest_session)`

The latest completed session uses the schedule's actual close, including early closes. Inputs are timezone-aware and normalized to UTC. XNYS schedule interpretation is anchored to `America/New_York`.

## Freshness Contract

Dashboard Overview and static snapshot manifests separate:

- actual completed dataset session;
- expected latest completed XNYS session;
- non-negative session lag;
- calendar freshness status;
- calendar ID and UTC checked-at timestamp;
- file/schema consistency validation status.

`fresh` means lag zero. `stale` means one or more completed XNYS sessions are missing. `unavailable` is a safe degradation when calendar evaluation cannot be completed. File/schema consistency wording is deliberately narrower than price correctness, corporate-action verification, or freshness.

The browser presents generated and checked timestamps in a human-readable named timezone while retaining exact UTC strings in the machine contract.

Static Snapshot freshness is a sealed publication-time assertion, not a live
clock. The browser labels it accordingly and treats `Data as of` as the durable
reference. The network-free current-context report separately evaluates the
latest canonical session and the active Snapshot session at report time while
preserving the immutable publication-time fields. See
[ADR 0149](../decisions/0149-separate-sealed-and-operational-freshness.md).
