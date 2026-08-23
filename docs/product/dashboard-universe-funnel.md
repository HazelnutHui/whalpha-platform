# Dashboard Universe Funnel

The Dashboard Funnel is a source-backed screening ledger, not a frontend reconstruction of summary counts. Dashboard contract 2.1 exposes ten ordered records per public Universe from immutable revision `authoritative-security-form-v2`.

For analysis session 2026-08-19 the official remaining-count sequences are:

- Common Shares: `4,565 → 4,192 → 3,992 → 3,967 → 3,049 → 3,002 → 1,718 → 1,718 → 1,718 → 1,718`
- Common Shares + ADRs: `4,565 → 4,565 → 4,358 → 4,322 → 3,271 → 3,218 → 1,831 → 1,831 → 1,831 → 1,831`

The stages are provider evidence base, target security form, supported exchange, comparable current/previous bars, previous close, complete 20-session history, trailing liquidity, outlier quarantine, reviewed overlay, and final membership. Each stage carries input, exclusion, and remaining counts; overlapping diagnostics are not substituted for sequential exclusions.

The frontend selects the matching ten-record ledger using the validated stable Universe ID. Primary remains first/default; Secondary remains second; Legacy is hidden. URL selection, refresh, and browser history retain the existing allowlisted keys. Old snapshot contract 1.3 is compatible but has no formal Funnel and must not display the former simplified reconstruction.
