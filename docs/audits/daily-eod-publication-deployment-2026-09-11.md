# Daily EOD Publication and Deployment Audit — 2026-09-11

## Scope

This audit records the guarded 2026-09-10 and 2026-09-11 daily data chain,
the rolling five-year census, and the 2026-09-11 Market Intelligence,
Dashboard Snapshot, Serving Bundle, and OCI deployment. It contains no
credential, provider response body, Session material, private-key path, or
server address.

## Daily data and calculation boundary

- The clean Dell source revision was
  `26cab64fabdafca710d6471cb09ac8c62ef17c2d`.
- A revision-bound owner-only data control passed its network-free preflight
  and allowed only Identity/EOD fetch and canonical Apply. Publication,
  deployment, scheduler mutation, order execution, SEC, and options authority
  remained false.
- 2026-09-10 Identity used 14 successful requests and produced 13,176 source
  identities plus 10,000 instruments/resolvers, with zero malformed rows and
  zero stable-ID collisions. Grouped Daily used one request and produced
  9,980 canonical rows from 12,572 raw records, with zero duplicate business
  keys and zero orphan references. The 383 case-sensitive provider-symbol
  rows were all explicitly ineligible rather than ambiguous.
- Eight 2026-09-10 offline stages completed. Its MI plan was correctly sealed
  as stale, lag one, after 2026-09-11 became the expected completed session;
  it was not published.
- The installed read-only timer naturally woke at 2026-09-11T20:30:10Z and
  selected 2026-09-11 as the sole missing session. It made zero provider
  requests and zero writes.
- 2026-09-11 Identity again used 14 successful requests and produced 13,176
  source identities plus 10,000 instruments/resolvers with the same zero
  malformed/collision gates. Grouped Daily used one request and produced
  9,971 canonical rows from 12,469 raw records, with zero duplicate business
  keys and zero orphan references. All 383 case-sensitive provider-symbol
  rows remained explicitly excluded, with zero ambiguous quarantine rows.
- Nine 2026-09-11 offline stages completed in about 17.1 minutes. Candidate
  was the hotspot at about 7.0 minutes and used one CPU core; observed RSS
  peaked near 11.2 GiB before returning downward. This remains a performance
  issue, not a data-integrity failure.

## Rolling five-year census

The post-Apply network-disabled census selected 1,255 XNYS sessions from
2021-09-13 through 2026-09-11.

- EOD covers all 1,255 target sessions with zero missing sessions.
- Point-in-time Identity covers all 1,255 target sessions with zero missing
  sessions. One additional Identity-only partition remains at 2021-09-10.
- Identity source observation covers 1,253 target sessions; 2026-08-13 and
  2026-08-19 remain unbound.
- Signal-eligible Membership covers only three sessions. The separate
  latest-vintage research-only Membership brings physical coverage to 303
  sessions but does not gain signal or performance authority.
- Instrument lifecycle and point-in-time classification remain absent.
  Corporate actions and the adjustment ledger remain bounded, split-only,
  and outcome-reconciliation evidence rather than complete point-in-time
  coverage.

The census therefore remains `quarantined` and does not authorize a real
backtest, performance claim, or model activation. Price depth is complete;
the five-year anti-survivorship research foundation is not.

## Publication and deployment

- MI plan SHA-256:
  `d7f69b5ef3b3fe091ebe2e8010d2241edf6245c4d481a91a45e8280160bb05d9`.
- Active Market Intelligence 1.3:
  `2026-09-11T205429Z-26cab64fabda`.
- Active MI pointer fingerprint:
  `42ee994c1818f8c48adfb7e0d337043845be8d8c4aa872907895a6984986ef29`.
- Snapshot plan SHA-256:
  `42e053e0b1f908e3a0355d7b63fa66c0bf4f8ac3c6201bb2da60970aadb17c2a`.
- Active Snapshot 1.11 / Dashboard 2.8:
  `2026-09-11T211340Z-26cab64fabda`.
- Active Snapshot pointer fingerprint:
  `a57ecbaef4f4ebc8bcda012193d7c07875f2bd7830a9a1eb6775c2819687e460`.
- Serving Bundle logical fingerprint:
  `22d95257fec4800ab20258f33ab8d4d45bed0f7f5aa8574046a9e6374ed5770d`.
- Deployment manifest SHA-256:
  `99f3ca1339102f5cf1dfcbb548d41d2891eaac9e75933c8b3115d364058a7536`.
- Checksums SHA-256:
  `a425a455599cfbe451319f7852b5ebe7a3efc4d0f81703861d79a74657c99b1c`.
- Final OCI state fingerprint:
  `b9b841f814da7ce1a960d87812cd6894f20478e81df96a6a117e73ce76fe07a6`.

The direct dry-run passed, Apply completed, and independent postflight matched
the release, clean source revision, bundle fingerprint, manifest, and
checksums. Nginx and the localhost-only Auth Service are active and enabled.
Protected routes and one bounded guest Session passed. Guest and credential
capability remain identical. There is no staging release, failed release,
failed unit, unexpected listener, credential, raw provider payload, or
Parquet in the Serving Bundle. Password login and final human visual review
remain manual checks.

## Final current-state reader

The 2026-09-11T21:24:38Z network-free current-context report found:

- 15,703 files / 5,935,786,680 bytes;
- inventory fingerprint
  `a83136b65d76371a9932aa58fc142aa815d1303dc89f600d852cc177eea36d5e`;
- zero symlinks and zero publication residue;
- EOD/Identity aligned at 2026-09-11;
- canonical and active Snapshot freshness both fresh, lag zero; and
- research readiness still `data_blocked`, with performance claims false.
