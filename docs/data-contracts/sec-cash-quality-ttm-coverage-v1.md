# SEC Cash-Quality TTM Coverage V1

This contract derives only issuer-level, source-traceable four-quarter CFO and
net income plus opening, closing, and average Assets from ADR 0303's ready-
endpoint package.

The input denominator is the exact ready endpoint count. Every output keeps
the closing fiscal coordinate, TTM values, both Assets boundaries, maximum
component knowledge time, contributing accessions, and source occurrence IDs.
Blocked endpoints remain in aggregate typed reason counts.

Economic fiscal cycles are keyed by issuer and duration origin. Source `fy` is
retained as reported evidence but never used to merge comparative periods or
prove cross-year succession.

The package is owner-only and closed-set: plan JSON, derived Parquet rows,
aggregate result JSON, and forward/reverse verification JSON. Atomic publish,
immutable modes, physical row replay, canonical JSON, and exact reread are
required.

This is source feasibility, not a security-level factor or source
qualification. See [ADR 0304](../decisions/0304-derive-issuer-level-sec-cash-quality-ttm-feasibility.md).

The first V1 package is retained as diagnostic evidence but is not governing:
its input selector used filing `fy` as identity and required a separate Q1
witness for Q2/Q3 origins. ADR 0305 freezes the corrected economic-endpoint
identity and requires a new versioned selector and disposition contract before
another real coverage build.
