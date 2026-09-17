# China A-share Stable Identity and Lifecycle Audit — 2026-09-17

## Scope

This audit closes only the stable listed-security identity and lifecycle gate
for the six-security SSE/SZSE pilot covering 2021-09-16 through 2026-09-16. It
does not create a daily historical Universe, expand to the full market, admit a
research panel, authorize canonical Apply, or publish Product data.

## Evidence and method

- retained exact current-list bytes for SSE Main Board, SSE STAR, and SZSE A
  shares plus the official SSE and SZSE delisting-source bytes;
- reconciled source security code, name, board, and listing date against the
  previously normalized official and BaoStock observations;
- keyed each listed occurrence by source security ID, exchange, board, and
  listing date under the market-specific stable-ID namespace;
- reproduced all six prior pilot IDs from that occurrence key, proving that
  the pilot join did not depend on ticker alone;
- reconciled one trading or suspended state for every instrument/session over
  all 1,211 sessions; and
- kept issuer-only evidence separate from listed-security termination
  evidence. No target appeared in either official delisting source.

## Result

| Decision | Count |
| --- | ---: |
| Planned pilot listed occurrence | 6 |
| Stable identity resolved | 6 |
| Identity quarantined | 0 |
| Complete five-year lifecycle interval | 6 |
| Incomplete lifecycle interval | 0 |
| Observed instrument/session states | 7,266 |

The exact SSE compact `YYYYMMDD` listing-date representation is normalized to
ISO date before comparison; a focused regression test protects this source
boundary. Code reuse or a later relisting date produces a different stable
identity and cannot silently join the earlier occurrence.

## Custody and verification

- package logical fingerprint:
  `406da4a55c0866c9087a48f6228bff235e788db0ae212cf37d3882b633f50249`;
- report logical fingerprint:
  `806c507e6aab194d904451592c8bd90d46a3bd6e3899b96df32b8dc480113338`;
- manifest physical SHA-256:
  `22bead84d73926d761860a66f288f7f9649ac6a64aabeefc034524432efea693`;
- 9 files, 3,416,370 bytes, owner-only modes, zero symlinks, closed file set;
- independent exact reread passed; and
- 67 focused A-share regression tests and all 3,141 backend tests passed.

The package is temporary owner-only evidence below `/tmp`. Every canonical,
research, Product, and deployment authority flag remains false. The next gate
is exactly one effective-dated daily Universe disposition for every evaluated
instrument/session.
