# Reconciled EOD Family-Evidence Apply Audit — 2026-09-12

## Boundary and authorization

Apply the two exact Historical Dataset Coverage Evidence manifests sealed by
ADR 0211 and no other canonical change. Execution used source revision
`cfed9d6cc1e0332d04bb3ee8fb168f66874617f0` and the explicit authorization
bound to:

- plan SHA-256
  `d328f1725dc4a74a6237d30e1ccdad6fa8c64765d45210a8cc7a76d6492f9168`;
- plan logical fingerprint
  `443d80c7347b794b7f105c2d8b5dc8e57fbc4d4dd67442773983647d69d0fcfc`;
- family-set fingerprint
  `30722680a6d2f8448db0e895fed7e060ca8a81f2d5faebca3b4d23fbba2b0d8e`.

The Apply was network-prohibited and held the global canonical-data lock. It
formally reread the plan and every transitive source before and after lock
acquisition, then published EOD first and Identity second as immutable atomic
directory targets.

## Exact result

Status: `applied`.

- published families: `eod_price_bar`, `point_in_time_identity`;
- published files: 2;
- published bytes: 2,673,980;
- formally reread families: 2;
- reused families: zero;
- external requests: zero;
- overwritten partitions: zero;
- deleted partitions: zero;
- outside-target inventory fingerprint before and after:
  `8baec95b3a4e81cc2b4ca05f9f1fb24a8a112237c6c217bf88c09066462aa307`;
- complete post-state fingerprint:
  `87a2a573b3350918a90db3cea51faaa1839a4e5fb420e2f20278dfc3cb9aa244`.

The Apply completed in 84.68 seconds. An immediate
`verify_then_complete` replay formally reread both completed targets, reused
both, and returned zero published files / zero bytes with the same full and
outside-target fingerprints. It completed in 101.66 seconds.

## Independent postflight

The credential-free current-context report completed at
2026-09-12T23:00:36Z:

- host/user `dell5820` / `hui` matched;
- canonical repository `main` at
  `cfed9d6cc1e0332d04bb3ee8fb168f66874617f0` was clean;
- canonical inventory: 18,174 files / 7,022,160,392 bytes;
- inventory fingerprint:
  `87a2a573b3350918a90db3cea51faaa1839a4e5fb420e2f20278dfc3cb9aa244`;
- symlinks: zero;
- publication residue: zero;
- historical family-evidence inventory: four partitions / four manifests,
  comprising the two prior rolling-current publications and these two exact
  corrected-edition publications.

## Authority and remaining blockers

Final Historical Coverage was not created. Research development and
performance authority remain false, and Production, Snapshot, serving bundle,
OCI, and website state did not change.

The read-only report remains `data_blocked`. Historical Membership is
incomplete; lifecycle is absent; corporate-action and adjustment coverage are
incomplete; Identity source observation has two quarantined gaps; costs,
revision lineage, a real chronological dataset, and a sealed real holdout also
remain incomplete. Publishing these two evidence manifests proves their exact
price/Identity source coverage but does not satisfy those independent gates.
