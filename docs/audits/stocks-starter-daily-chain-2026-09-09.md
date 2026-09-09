# Stocks Starter Daily Chain Audit — 2026-09-09

## Outcome

The first controlled same-session run under
`massive_stocks_delayed_15_minutes` completed from provider acquisition through
independently verified OCI deployment. Engineering diagnosis time is excluded
from the measured stage durations below.

## Canonical data

- Identity: 14 successful requests; 9,982 Instruments, 13,158 provider
  identities, and 9,982 Resolvers.
- EOD: one successful request; 12,468 raw rows and 9,916 canonical rows; zero
  duplicate business keys and zero orphan Identity references.
- Identity and EOD are aligned at 2026-09-09.
- Membership: 19,964 signal-eligible decisions; exact Plan/Apply and
  zero-write verify-then-complete passed.
- Final `/data`: 4,311 files / 2,321,416,033 bytes; inventory fingerprint
  `0cbc099b84b084641f97d87bc0eb94a57fad279c41aa5a4d47554e4138b395f0`;
  zero symlinks and zero publication residue.

## Analytics and serving

- Nine offline actions completed in about 15.7 minutes. Candidate was the
  largest stage at about 6.3 minutes, peaked near 8.2 GiB, and used one CPU
  core.
- Market Intelligence:
  `2026-09-09T205635Z-e06bd62ecab3`.
- Snapshot and Serving Bundle:
  `2026-09-09T211131Z-e06bd62ecab3`.
- Serving Bundle logical fingerprint:
  `233dd2c912f463f4360dbb2247160f4998cd777e2600a440cec6cafb348842e9`.
- Snapshot planning took about 3.8 minutes; Serving Bundle construction about
  2.1 minutes; OCI deployment about 2.4 minutes.

## Production postflight

The independent remote inspector matched the target release, source revision
`e06bd62ecab3cbf65867c9ddd9853a909379af9a`, bundle fingerprint, manifest,
and checksums. Nginx and the localhost-only Auth Service are active/enabled;
protected routes and a temporary guest Session passed; guest and credential
route policy is identical. There are no staging releases, failed releases,
failed system units, or unexpected private listeners. Credential login and
visual appearance remain manual checks.

## Integration findings

No failed attempt wrote production state. ADR 0190 addresses the three defects
observed before compatibility completion: shared Identity/EOD persistent
artifact slots, coordinator `/tmp`-only MI/Snapshot approval custody, and a
Membership post-action clock inversion. The installed daily timer remains
read-only; no unattended write-capable scheduler was enabled.

This audit proves one successful same-evening Starter observation. It does not
prove a guaranteed provider finality minute, five-year endpoint depth,
Historical Coverage, research readiness, strategy performance, or option
returns.
