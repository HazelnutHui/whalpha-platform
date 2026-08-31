# ADR 0110: Probe account entitlement separately from historical acquisition

## Status

Accepted.

## Context

Historical research is blocked by both technical account capability and broader
source-permission/lifecycle evidence. Conflating them prevents a small technical
check, while treating endpoint access as permission would be equally unsafe.

## Decision

Add a four-request Massive capability probe for one exact historical session:
unadjusted Grouped Daily, point-in-time active Tickers, Splits, and Dividends.
It records only endpoint, safe status, result count and retry metadata. It does
not retain response bodies, write data, determine permission, authorize the
Historical Pilot, or retry automatically.

Execution requires a clean exact Git revision and a user acknowledgement bound
to that revision, session and contract. Review mode loads no credential and
makes no request. Technical accessibility is evidence about account entitlement
only; it is not a license, completeness, quality, retention or display finding.

## Consequences

- Engineering may establish whether the current account exposes four required
  endpoint classes without weakening Historical Pilot approval.
- The probe cannot backfill, map, publish or write `/data`.
- Inactive Tickers and lifecycle/terminal evidence remain outside this probe.
- Commercial-grade source permission remains an eventual publication and
  operation requirement, but does not justify fabricating a technical result.
