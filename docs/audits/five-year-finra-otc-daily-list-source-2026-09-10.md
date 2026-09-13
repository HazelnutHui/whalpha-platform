# Five-Year FINRA OTC Daily List Source — 2026-09-10

## Scope

Acquire and formally reread official FINRA OTC Daily List evidence from the
Membership support boundary 2021-08-11 through the five-year evaluation end
2026-09-09. This is owner-only source custody outside `/data`; it performs no
stable-ID resolution, canonical write, analytics, publication, deployment, or
scheduler change.

The acquisition ran from clean source revision
`2b1409687377976f4c4d5d07a68c3a6d10c1f741`. Each month used all 60 reviewed
fields, 500-row pages, one-second serial pacing, zero automatic retry, and
immutable formal checkpoints under the branch-local decision later adopted by
main ADR 0215.

## Completed physical evidence

The network-free transitive census at 2026-09-10T12:04:22Z established:

- exact monthly partitions: 62;
- requests: 163;
- source observations: 68,714;
- distinct `OTCDailyListID` values: 68,710;
- data versions: all 62 packages reported version 1;
- retained page bytes: 122,793,144;
- physical custody: 350 files / 123,236,069 bytes;
- symlinks / partial packages: zero / zero;
- event counts: DA 24,828; DC 13,922; DD 639; SA 10,375; SC 9,564;
  SD 9,386;
- package-chain fingerprint:
  `f40142ea94d4c5d43f594fc65e3a616831b0770c8237c09d455e3ba1b1589c0c`;
- sealed range-census logical fingerprint:
  `badd20a33f0b668c5a39cfb4d45e86c0daf7b2c229c655a242436a07b9d95f41`.

All completed package documents/pages and the range census are mode `0400`;
package/root directories are mode `0700`; package locks are mode `0600`.
The repository-root API regression passed 2,421 tests with two unchanged
dependency deprecation warnings after the range reader and sealed census were
added.

## Repeated source-identifier evidence

Four identifiers each occur twice with different payloads, producing four
additional occurrences rather than four silently discarded rows:

| ID | Dates | Event / symbol | Observed difference |
| --- | --- | --- | --- |
| 316233 | 2025-11-10, 2026-02-20 | DA / LUGDF | date, comment, and security-description spacing |
| 320719 | 2026-01-27, 2026-02-06 | DA / LWCL | date and later comment |
| 321351 | 2026-02-06, 2026-02-10 | DC / PHIG | date and other event payload fields |
| 331496 | 2026-07-21, 2026-07-23 | SD / GOCOQ | date and materially revised bankruptcy/distribution comment |

This proves `OTCDailyListID` cannot be treated as a globally unique immutable
event key. The observations are compatible with provider update, correction,
or identifier-reuse behavior, but the source evidence does not distinguish
those explanations. Every occurrence remains intact and downstream resolution
must use its located full-row fingerprint. None is canonicalized here.

## Alignment decision

The source-custody stage is complete with repeated identifiers explicitly
preserved. It materially expands OTC additions, deletions, symbol changes,
bankruptcy flags, distributions, and split/action evidence, but the lifecycle
family remains incomplete. The next bounded stage is stable-ID/semantic
resolution against the completed Identity history and action packages, with
major-exchange and terminal residuals left quarantined or assigned to another
measured source. No paid source is justified merely by this package count.
