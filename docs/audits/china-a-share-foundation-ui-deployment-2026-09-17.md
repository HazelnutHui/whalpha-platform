# China A-Share Foundation UI Deployment Audit — 2026-09-17

## Scope

Deploy the already tested, identifier-free A-share foundation status view to
the public entry and protected Quant Research Lab. The deployment reused the
existing immutable U.S. Snapshot and did not refresh EOD, write `/data`,
publish A-share row-level data, or open A-share research authority.

## Immutable bindings

| Field | Value |
| --- | --- |
| Source revision | `34488cb022bdba3275afcd048637505ec960c786` |
| OCI release | `2026-09-17T052618Z-34488cb022bd` |
| Dashboard Snapshot | `2026-09-11T211340Z-26cab64fabda` |
| Snapshot / Dashboard contract | 1.11 / 2.8 |
| Market Intelligence publication | `2026-09-11T205429Z-26cab64fabda` |
| Market Intelligence contract | 1.3 |
| Bundle file count | 63 |

## Execution and verification

The workstation bundle build completed from a clean `main` worktree. The OCI
deployment dry-run passed remote preflight and Nginx configuration validation.
The apply completed upload, checksum verification, atomic release switch,
Nginx validation, and route checks.

An independent read-only inspection at `2026-09-17T05:27:20Z` verified:

- active release and source revision match the immutable bindings above;
- manifest SHA-256 is
  `b0c62d92b5e7deba7fa6ba534a51ca55e8c7a6c5c50827a73cbd9f2713f8ad85`;
- checksums SHA-256 is
  `7ea9017eea67becb59719e0acaaf9f89c96c08050d25a1fd9ced2eb1cf497018`;
- bundle logical fingerprint is
  `74cb49d3134b5845588023fbfec8414e27598c861321ca32d2c767e2f4aad01e`;
- Nginx and authentication services are active and enabled;
- the authentication listener is localhost-only with no unexpected private
  listener;
- protected routes and a temporary guest Session pass;
- guest and credential routes retain identical policy; and
- no failed release, staging release, or failed system unit remains.

Password login was not exercised because the inspector does not read
credentials. Final browser appearance remains a human visual check. The UI
describes six bound SSE/SZSE pilot securities, 1,211 sessions, 7,266 mechanics
decisions, completed and blocked admission families, and zero A-share factor
campaigns. Those facts remain presentation only; no A-share backtest, Alpha,
model, candidate ranking, Product publication, or trading authority was
granted.
