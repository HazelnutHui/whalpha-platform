# 2026-08-30 Daily Universe Membership Physical Pilot

## Result

`MECHANICS_ONLY_RECONSTRUCTION_COMPLETED`

The Dell-local pilot formally reread the completed reviewed full-base revision
for analysis session 2026-08-19 and wrote an immutable Membership manifest 1.1
partition only below `/tmp/tip-membership-pilot-20260830-v2`. It made no
provider request and changed no canonical `/data`, active artifact, or
Production state.

## Source boundary

- Analysis session: `2026-08-19`
- Membership evidence as-of date: `2026-08-14`
- Reviewed source completion/cutoff: `2026-08-21T00:00:00Z`
- Reviewed source logical fingerprint:
  `51403e939930265ba1a273e9f8bc2113cb455f22e8437c1d2775005fd293ee97`
- Metric base: 4,565 stable IDs; fingerprint
  `8fcbf1f42f559ffe8e6174732c8f761632554dc36aa85da806213fcac540a691`
- Complete source decisions: 9,130; fingerprint
  `bf17e288bed7cf51925a2bc73ab89b6e09e17142d2a41db9624e2370ed693aab`

Because the reviewed source completed after the analysis session, every
non-quarantined output row is `warning` with
`reconstruction_source_cutoff_after_session`. The partition is explicitly
`reconstructed_point_in_time`, not `as_operated`, and is not eligible for an
anti-look-ahead performance claim.

Quality totals are 8,969 `warning` and 161 `pending_review`; all 9,130 rows
retain the late-cutoff reason.

## Output reconciliation

| Universe | Included | Excluded | Quarantined | Evaluated |
| --- | ---: | ---: | ---: | ---: |
| Primary Common Shares | 1,718 | 2,775 | 72 | 4,565 |
| Secondary Common Shares + ADRs | 1,831 | 2,645 | 89 | 4,565 |

- Total rows: 9,130
- Evaluated-base fingerprint:
  `3631bc6f4ac03c755aed2902854484e1c7e3f3aff76b770917b6563b7293e253`
- Output logical fingerprint:
  `9b0ba33224f98cf42643f2fc52714769f5e38503b45b727d439ec7f8e1b320b3`
- Output Parquet SHA-256:
  `5128c2617c1478f4c1535d2d46b3ad69b8b356762042acbb9b03e420d34df230`

The formal reader verified the manifest, Parquet schema and physical hash,
logical row fingerprint, deterministic ordering, unique business keys, exact
same-base coverage, uniform provenance, and disposition totals. A repeated run
with the same evaluation clock returns `already_present`.

## Remaining boundary

This proves one physical conversion path only. No Membership source exists for
the other retained sessions, and the current Activation must not be projected
backward. Corporate-action, lifecycle/terminal, adjustment, and 252-session
coverage blockers remain unchanged.
