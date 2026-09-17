# China A-Share Pilot Market-Mechanics Audit — 2026-09-17

## Scope

This bounded gate reconstructs effective-dated trading rules, statutory fees,
one account-cost research scenario, and theoretical daily price limits for the
existing six-security SSE/SZSE pilot from 2021-09-16 through 2026-09-16. It
reads the immutable daily and official-calendar packages and writes only an
owner-only package below the dedicated `/tmp` pilot boundary. It does not
write canonical data or authorize research, Product, publication, or
deployment.

## Official evidence

Thirteen exact official HTML payloads were captured and retained from SSE,
SZSE, CSRC, tax, and government sources. The bounded registry covers:

- SSE main-board and STAR trading rules;
- SZSE main-board and ChiNext trading rules;
- the 2026-07-06 main-board risk-warning limit change from 5% to 10%;
- seller-only stamp duty and its 2023-08-28 reduction;
- exchange handling fees and their 2023-08-28 reduction;
- securities regulatory fees;
- the 2022-04-29 A-share transfer-fee reduction; and
- the official commission composition and CNY 5 minimum standard.

Every final URL remained on the approved official-host allowlist. The package
retains final URL, content type, byte count, and SHA-256 beside the exact raw
payload. Later-published official pages that describe an earlier rule are
retrospective rule evidence; their publication time is not silently rewritten
as earlier point-in-time knowledge.

## Deterministic result

- official source references: 13;
- effective-dated trading rules: 10;
- effective-dated fee rules: 14;
- pilot price-limit decisions: 7,266;
- observed bars outside theoretical limits: zero;
- unresolved price-limit rules: zero;
- files: 20;
- total package bytes: 5,934,265;
- report logical fingerprint:
  `8c02b856a0214c4b759f3095c5b7bdd145817e3dca831982a7e42df03be83676`;
  and
- package logical fingerprint:
  `799a5511871e826bb031651d01077e789392358b0b77198ca41d77f1d724da25`.

Theoretical prices use the previous close, the effective ratio, half-up
rounding, and a CNY 0.01 tick. They remain explicitly distinct from exact
exchange-observed limit prices. Suspended state-only sessions retain decisions
without inventing bars.

## Account-cost boundary

The registered scenario uses the user's reported Ping An Securities rate
through Tonghuashun of 0.01% per side. It conservatively applies a CNY 5
minimum and 5 bps per-side slippage. Commission is provisionally treated as
all-in so regulatory and exchange-handling fees are not double-counted;
transfer fee and sell-side stamp duty remain separate.

The all-in interpretation, minimum applicability to the actual account, and
historical backcast are not broker-statement facts. They remain explicit
research assumptions and require scenario stress tests or account-statement
confirmation before admitted performance use.

## Custody and authority

The package uses canonical JSON, physical hashes, logical fingerprints,
owner-only file modes, atomic rename, a closed file set, and a complete exact
reread. Corruption tests prove that changed raw bytes fail closed. The package
fixes canonical Apply, research backtest, Product publication, and deployment
authority to false.

## Verdict

`SSE_SZSE_PILOT_MARKET_MECHANICS_RECONCILED`

The next independent gate is adjustment-factor and corporate-action economics,
followed by listed-security lifecycle, daily historical Universe decisions,
full-market expansion, and the complete 13-family admission report.
