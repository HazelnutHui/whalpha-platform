# Daily EOD Publication and Deployment Audit — 2026-09-06

## Scope

This audit records the guarded 2026-09-04 daily catch-up, offline analytics,
publication, Snapshot, serving-bundle, OCI deployment, and independent
postflight performed from the Dell source-of-truth repository. It records no
credential, provider response body, Session material, or server address.

## Canonical acquisition and Apply

- Identity fetch used 14 bounded requests and froze 13,155 provider-identity
  rows plus 9,982 Instrument and Resolver rows. Plan SHA-256:
  `306375c85644cb3cc53c3676823e0dfda89bb9defc17f7c107f30d74029d5b20`.
- EOD fetch used one adjusted-false request. Formal mapping produced 9,962
  canonical rows, zero duplicate business keys, and zero orphan references.
  Plan SHA-256:
  `281fff7cef549e8a5d51c2022a78e2b980f9cee3f0d866221d8fba9b5a555767`.
- Both Apply operations completed `published_and_verified` through their
  existing immutable-plan and compare-and-swap boundaries.
- Canonical EOD now contains 304 contiguous XNYS sessions from 2025-06-23
  through 2026-09-04. Latest EOD fingerprint is
  `3266c411a556ee1813a73beae19a71dc14e855b476770b3b82f81a5151e4abc4`.
- The 2026-09-04 Identity fingerprint is
  `5eed9166d609cea7693aed324908427f113ab72c221921690bcbdc29f71727f7`.

The routine daily Identity catch-up does not also normalize a historical
source-observation partition. Canonical normalized source custody therefore
remains 301 partitions and now reports three explicit gaps: 2026-08-13,
2026-08-19, and 2026-09-04. This does not affect current Identity/EOD alignment,
but it remains a Historical Coverage blocker.

## Offline analytics and publication

All coordinator-owned 2026-09-04 actions completed with zero external request
and zero Production write: Phase 1a, Sector ETF Rotation, Phase 1b, Candidate,
Entry Geometry, ETF Relationships, Market Preview, Strategy Channels, and
Candidate Visual Context. The resulting Candidate audit fingerprint is
`d0e01e1aa795c94ba5f3f159fbd0fa1c4165fda25dc13a7bc7a6bbe2ea5c0819`.

The fresh Market Intelligence 1.3 publication is
`2026-09-04T112916Z-717cb82c5369`; its payload SHA-256 is
`34f9ae867d44aae4fda77ed47d2921570a52aade1147869f1c7835439f2439c8`.
The fresh Snapshot 1.11 / Dashboard 2.8 release is
`2026-09-04T113333Z-717cb82c5369`; its active-pointer fingerprint is
`e6b23d40e52f14e3b77c564061531c7b339540ebf07c0fb8a1be18b9ea113cc7`.
Both were lag-zero and required no stale-review exception.

The published Market Regime is Balanced: Primary 56.7472 and Secondary
57.3733. Candidate display counts are 880 and 951 respectively. Market
Intelligence still consumes only 26 sessions and correctly remains
`degraded_short_history`.

## Serving bundle and OCI proof

The exact 51-file serving bundle has logical fingerprint
`d2b0c66cb246e0bf7af6d48ebe59ef8a4c95f9ef259a32b7013f06e72ee54616`,
manifest SHA-256
`20e56e74f66bbf60d1b8bfa5839934ca240a66d9a49abd3bbad7d1038943334b`,
and checksum-file SHA-256
`82065c12658eb9c75597a2073920c2f866db07c676fedb86d2b733de5a21fd7b`.

Deployment completed through the reviewed one-shot capability. Independent
postflight matched the exact release, source revision, bundle fingerprint,
manifest, and checksums. Nginx and the localhost-only Auth Service are active
and enabled; protected-route behavior, temporary guest Session, Dashboard,
Snapshot, Candidate summary/detail, Strategy Channels, Sector ETF Rotation,
logout, and guest/credential capability parity passed. Failed system units,
staging releases, partial releases, and failed-release residue were all zero.
Password-based login and final human visual inspection were not exercised.

## Final Dell state

- `/data`: 4,011 files / 1,963,053,417 bytes;
- inventory fingerprint:
  `2a4535a92f7b4224509b33677fca1cb4ff11e7b863f74e0bd92b6a22ea2dce45`;
- symlinks and publication residue: zero;
- research readiness: `data_blocked`;
- no historical backfill or transient computation service is running.

This run validates the complete manual/agent-run daily chain under the standing
workflow direction. It does not authorize an unattended write-capable
scheduler, a research performance claim, a model change, or a new data source.
