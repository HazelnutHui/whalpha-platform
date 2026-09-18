# SEC Cash-Quality TTM Coverage V2

The input is exactly ADR 0305's canonical direct-origin endpoint package. The
plan binds its verification/result identities and its row file's logical hash,
physical hash, schema, byte size, endpoint count, and query-row count. Access
to the target index, normalized source, and network is forbidden.

Every input endpoint is dispositioned once as TTM-ready or under one typed
fail-closed blocker. The economic sequence uses duration origin and explicit
period end, never filing `fy`. Valid sequence order is Q1, Q2, Q3, FY within
one origin and FY to a Q1 whose origin is prior FY end plus one day. Annual
durations must be 350–378 days. Ambiguous period ends, missing history, gaps,
invalid annual shapes, unprovable arithmetic, and zero average Assets remain
blocked.

Each output contains fiscal-year origin, TTM CFO and net income, opening/closing/average Assets,
the maximum component knowledge time, contributing accessions, and complete
source-occurrence lineage. It is issuer evidence and is not a security-level
factor.

The owner-only closed set contains plan JSON, issuer TTM Parquet rows,
aggregate result JSON, and forward/reverse verification JSON. Atomic publish,
immutable file modes, canonical JSON, byte-identical replay, and exact reread
are mandatory. See [ADR 0307](../decisions/0307-run-corrected-economic-endpoint-sec-cash-quality-ttm-coverage.md).
