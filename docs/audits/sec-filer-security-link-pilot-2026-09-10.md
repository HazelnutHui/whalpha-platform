# SEC Filer-to-Security Link Pilot — 2026-09-10

## Scope

This was one real, network-free, owner-only Dell pilot for XNYS session
2023-11-09. It read the existing canonical Massive Instrument Master and
Provider Identity plus their normalized Identity source custody. It wrote no
canonical `/data`, analytics, Membership, publication, deployment, or
scheduler state.

The implementation was clean source revision
`0a40957006c1f5e971d81bcd85f20994544fcfb8` under contract
`sec-filer-security-link-decision/1.0`.

## Result

- canonical stable-security denominator: 8,201;
- admitted unique-CIK links: 7,345;
- quarantined missing-CIK decisions: 856;
- conflicting-CIK or Identity-mismatch decisions: zero;
- unique admitted CIKs: 5,167;
- multi-security CIK groups: 150;
- source-custody gaps: zero; and
- every output row retained `issuer_projection_authorized=false`.

Input Provider Identity states reconciled to 8,201 resolved, 791 unresolved,
2 ambiguous, and 2,236 excluded source rows. Common stocks contributed 5,066
admitted and six missing-CIK decisions. ETFs contributed 2,279 admitted and
850 missing-CIK decisions.

The largest one-to-many group contained 301 securities under one CIK. This is
not treated as a stable-ID collision. It is evidence that filer identity may
represent a fund complex, trust, issuer, or other structure with many listed
securities. No primary share class was selected and no SEC fact was projected
onto those securities.

## Time boundary

The source-custody contract was `eligible_at_source_observed_at`, with actual
Dell observation at 2026-09-10T16:15:59.206933Z. The pilot therefore does not
claim that the reconstructed Identity/CIK relationship was available at a
2023-11-09 signal cutoff.

## Custody and verification

The completed package is retained at the owner-only Dell source-state root
`historical-source/sec-filer-security-link-pilot/build=2023-11-09-v1`.

- Parquet: 583,210 bytes;
- manifest: 2,883 bytes;
- manifest SHA-256:
  `385fed347850a225c53cbc85f68a1d56bcfa8b172982c3d08cddf543e9879f01`;
- content fingerprint:
  `a622d0d8052574f6d9150379639345c09916ea0e811cf64f9c22bb69053db86d`;
- manifest logical fingerprint:
  `e7efd0f6b530be218e6c64cea71a8f4fa7be4c2febc55d3098a8681d08c28421`;
  and
- schema fingerprint:
  `0a9cfe7276893980ee82eb50fadafeb30bb10593867f3a57fa47d01aa2fad793`.

The build performed its own full formal reread and transitive source
validation. The complete API regression passed 2,445 tests with the two
unchanged dependency-deprecation warnings.

## Decision

The pilot is a GO for the exact five-year candidate build after the active
EOD/Identity writer becomes quiescent. Any still-absent 2026-08-13 and
2026-08-19 source-custody partitions must be supplied as an explicit missing
set and produce quarantined daily decisions; they may not be silently skipped.
The resulting candidate will still grant no issuer projection, point-in-time
performance, canonical publication, or Production authority.
