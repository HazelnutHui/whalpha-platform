# Bounded Identity Extension Evidence Audit — 2026-09-13

## Scope

Build and independently verify one no-write Identity-only family-evidence plan
for the exact canonical sessions 2026-09-08 and 2026-09-09, execute its later
exact authorization, and measure the resulting corporate-action resolution
delta. No provider, network, Historical Coverage, research, Candidate,
Production, website, deployment or scheduler operation was performed.

## Implementation validation

- Clean implementation revision:
  `d6ada7de6c9e0d374ef63f07d54c58bff594d5bb`.
- Related evidence-plan, Apply, current-mechanics, reconciled-edition and
  historical-Identity tests: 69 passed before the final full run.
- Complete API suite: 2,592 passed in 263.77 seconds with two unchanged
  dependency deprecation warnings.

## Exact source scope

Both snapshots passed the existing formal Instrument Master snapshot reader.

| Session | Instruments | Provider identities | Resolvers | Snapshot fingerprint |
| --- | ---: | ---: | ---: | --- |
| 2026-09-08 | 9,982 | 13,155 | 9,982 | `ccada891e47725796142b08381e4a24026ee074d8d5dc4cf1d33b9fbc7e422a5` |
| 2026-09-09 | 9,982 | 13,158 | 9,982 | `f29de23284b163955fc542b2c48ed3ebd60b618493366511935164e574694707` |

The Identity evidence contains two snapshot artifacts, 19,964 instrument
records and 14 physically hashed source files: two completion manifests plus
six partition manifest/payload files per session.

## Exact no-write plan

- Plan custody:
  `/tmp/whalpha-identity-extension-2026-09-08-09-plan.json`
- Custody state: owner/group `hui:hui`, regular file, mode `0400`, 5,250 bytes.
- Plan SHA-256:
  `f099929d17c07695d3b468910e1c7233bed74bab1714a81ad1189dc9cfb7317a`
- Plan logical fingerprint:
  `e4111aef103cc7822228dc285fb3810d118415805b8def76ef057e77b04fe4e4`
- Family-set fingerprint:
  `c559851362c81f1c9cc08204a902aaa203938c70eca30a02525f7904cdaea6c5`
- Identity-evidence logical fingerprint:
  `35a45e158ffdedc2cd3f3667495bbb4fdd5841a70c02370e3c0baa80d5fa51d5`
- Evidence manifest SHA-256:
  `aaa7535253acf910b5cb6299a34ff4f33f04544aa8447bec3fd599bea13e1c68`
- Planned canonical delta: one new 3,623-byte manifest.
- Exact target:
  `market-data/historical-coverage-evidence/schema_version=1/family=point_in_time_identity/evidence_id=35a45e158ffdedc2cd3f3667495bbb4fdd5841a70c02370e3c0baa80d5fa51d5/manifest.json`

The target was absent at planning and independent verification. A second CLI
reread reproduced every identity, count, hash and authority field. Planning
reported zero external requests, zero canonical writes, `apply_authorized`
false, and false Historical Coverage, research-development and performance
authority.

## Authorized Apply and recovery

The user supplied the exact authorization string containing the approved plan
SHA-256, logical fingerprint and family-set fingerprint. Apply published only
the planned `point_in_time_identity` manifest:

- published files / bytes: 1 / 3,623;
- overwritten / deleted partitions: 0 / 0;
- external requests: 0;
- formal reread families: 1;
- pre/post outside-inventory fingerprint:
  `87a2a573b3350918a90db3cea51faaa1839a4e5fb420e2f20278dfc3cb9aa244`;
- complete post-state fingerprint:
  `eda858b1db23dc58f22cdd0faa290f2141691fecf15862dc5bd6d095354834ff`.

Immediate completed-state recovery reused the same Identity evidence, wrote
zero files / zero bytes, repeated the formal reread, and reproduced both
inventory fingerprints. The target directory is mode `0755`, its sole
manifest is mode `0644`, owner/group `hui:hui`, and canonical postflight found
18,175 files / 7,022,164,015 bytes, zero symlinks and zero staging/partial
residue.

## Reconciled corporate-action result

A preceding read-only exact-date join found that these snapshots can resolve
206 of the 343 post-boundary corporate-action rows: 96 on 2026-09-08 and 110
on 2026-09-09. A new owner-only `build=20260913-v2` resolution shadow then
proved exactly that delta while retaining the old version:

- resolved: 129,292, up 206 from 129,086;
- unresolved: 112,943, down 206 from 113,149;
- exact-date Identity unavailable: 3,513, down 343 from 3,856;
- exact-date Identity available: 238,722;
- unresolved ticker: 109,430, including the 137 newly inspected rows whose
  ticker truly remains absent on its event date;
- seven missing/invalid-ticker source rows remain separately unrepresentable;
- logical fingerprint:
  `444077fb1ca39ba3ac210f19fc19dae7e94573d42fa3d1c4119216b2641a7c4a`;
- manifest SHA-256:
  `b0d3e7438f8a1bd3d643a5fab564634fa203f92f08175dc9ceb5e166b1597c66`.

The 14-file shadow is 17,112,232 bytes, mode `0700` directories / `0400`
files, with zero symlinks or staging residue. A separate formal reread
reproduced all counts and fingerprints.

The new assignment-free `build=20260913-v2` unresolved census scanned all
1,253 evidence-bound Resolver sessions with eight processes. It accounts for
all 112,943 residual rows as 89,074 zero-candidate, 23,676 one-candidate and
193 multiple-candidate rows. The 13,780 unique tickers split into 11,433 /
2,307 / 40 respectively. It retains 2,387 candidate relations across 2,363
candidate instruments and still assigns zero stable IDs. Its logical
fingerprint is
`42a3b34e8354832c6505ac4a4c645145a2800390d0cfb99e12d31408cafe7f98`;
manifest SHA-256 is
`f1fbc2f8b76c34b3b44ff80c6292e458126762fe455f6e1953b759a642fd7f48`.
The two-file census is 3,781,863 bytes with the same owner-only custody and no
symlink or residue.

The evidence publication and the two private shadows do not establish final
Historical Coverage or research eligibility. The remaining 112,943 rows,
particularly 89,074 zero-candidate rows and 23,676 one-candidate rows outside
proved event-date ownership, remain lifecycle/security-scope evidence work.
