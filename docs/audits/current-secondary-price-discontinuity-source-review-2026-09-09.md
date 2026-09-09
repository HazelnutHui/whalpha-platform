# Current-Secondary Price Discontinuity Source Review — 2026-09-09

## Result

The 14 stable IDs / 15 flags in the frozen current-Secondary locator sample
were reviewed against issuer investor-relations pages, issuer-filed SEC
exhibits, and one OCC corporate-action memo. Thirteen flags have date-aligned
first-party market-event context, one has explicit non-split cash-distribution
evidence, and one has same-day issuer context that does not adequately explain
the observed direction or magnitude.

No split fact was established. Date alignment is not proof that an event caused
a price move, and absence of a split announcement from this bounded search is
not proof that no split occurred. No canonical action, adjustment factor,
historical identity, Membership, or research eligibility changed.

## Evidence review

| Current locator / transition | First-party evidence | Review disposition |
| --- | --- | --- |
| NKTR, 2025-06-24, 2.0881 | Nektar reported positive Phase 2b REZOLVE-AD results on the flagged morning ([issuer IR](https://ir.nektar.com/node/21996)). | Date-aligned clinical event context; no split inferred. |
| PRAX, 2025-10-16, 2.7601 | Praxis reported positive results from two pivotal Phase 3 Essential3 studies that morning ([issuer IR](https://investors.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1)). | Date-aligned clinical event context; no split inferred. |
| MBX, 2025-09-22, 2.2400 | The issuer-filed 8-K exhibit reports that canvuparatide achieved the Phase 2 primary endpoint ([issuer SEC exhibit](https://investors.mbxbio.com/static-files/7487f79f-a8c1-4d3c-aee7-6d07722b5a91)). | Date-aligned clinical event context; no split inferred. |
| ABVX, 2025-07-23, 6.3100 | Abivax announced positive Phase 3 ABTECT results after the prior U.S. close ([issuer IR](https://ir.abivax.com/news-releases/news-release-details/abivax-announces-positive-phase-3-results-both-abtect-8-week/)). | Prior-evening clinical event context; no split inferred. |
| KD, 2026-02-09, 0.4615 | Kyndryl released quarterly results, updated outlook, disclosed leadership changes, and delayed its 10-Q that morning ([issuer IR](https://investors.kyndryl.com/news-releases/news-release-details/kyndryl-reports-third-quarter-fiscal-2026-results)). | Date-aligned earnings/event context; no split inferred. |
| DFNS, 2026-07-31, 0.4354 | T3 Defense issued a same-day operating-performance update ([issuer IR](https://investors.t3dfns.com/pressreleases/detail/11511caf-8e5a-4df2-92f0-fd57c0887f17)). | Context found, but it does not establish the reason for the downward gap; unresolved. |
| BMNR, 2025-06-30, 3.5170 | BitMine filed an 8-K describing a $250 million private placement, Ethereum treasury strategy, and chair appointment ([SEC](https://www.sec.gov/Archives/edgar/data/1829311/000168316825004802/bitmine_8k.htm)). | Date-aligned financing/strategy event context; no split inferred. |
| CELC, 2025-07-28, 3.3377 | The issuer-filed 8-K exhibit reports positive Phase 3 VIKTORIA-1 topline data ([issuer SEC exhibit](https://ir.celcuity.com/static-files/4f41e291-48de-4ae7-8720-cb9722b2e2c4)). | Date-aligned clinical event context; no split inferred. |
| ALMS, 2026-01-06, 2.6715 | Alumis reported positive results from two Phase 3 ONWARD studies ([issuer IR](https://investors.alumis.com/news-releases/news-release-details/alumis-envudeucitinib-delivers-leading-skin-clearance-among-next)). | Date-aligned clinical event context; no split inferred. |
| ALMS, 2026-09-01, 0.4553 | Alumis reported that the Phase 2b LUMUS trial missed its primary and secondary endpoints in the overall population ([issuer IR](https://investors.alumis.com/news-releases/news-release-details/alumis-announces-topline-results-envudeucitinib-phase-2b-trial)). | Date-aligned clinical event context; no split inferred. |
| SION, 2026-08-10, 0.0950 | Sionna reported a missed key activity endpoint and that it would not advance SION-719 as an add-on to standard of care ([issuer IR](https://investors.sionnatx.com/news-releases/news-release-details/sionna-therapeutics-reports-topline-data-two-development)). | Date-aligned clinical event context; no split inferred. |
| GRAL, 2026-02-20, 0.4891 | GRAIL reported results and NHS-Galleri topline data after the prior session; the stated primary endpoint was not met ([issuer IR](https://investors.grail.com/news-releases/news-release-details/grail-reports-fourth-quarter-and-full-year-2025-financial)). | Prior-evening earnings/clinical event context; no split inferred. |
| VISN, 2026-04-28, 0.4936 | OCC memo 58754 records a $10-per-share special cash distribution with an April 28 ex-distribution date and an adjusted option deliverable ([OCC](https://infomemo.theocc.com/infomemos?number=58754)). | Explicit non-split distribution evidence; keep split factor absent and total-return work blocked. |
| EYPT, 2026-08-17, 0.2753 | EyePoint reported that the LUGANO Phase 3 primary endpoint was not achieved in the full dataset ([issuer IR](https://investors.eyepoint.bio/news-releases/news-release-details/eyepoint-announces-topline-data-lugano-first-two-pivotal-phase-3)). | Date-aligned clinical event context; no split inferred. |
| COGT, 2025-11-10, 2.2105 | Cogent reported positive Phase 3 PEAK results that morning ([issuer IR](https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-reports-positive-results-bezuclastinib-peak)). | Date-aligned clinical event context; no split inferred. |

## Interpretation

The severe-ratio diagnostic is useful as a high-recall review screen, but the
current sample demonstrates why it cannot classify missing splits by itself:
large biotech trial outcomes, earnings, financing, strategy changes, and cash
distributions can all produce the same numerical shape.

The sample also identifies two distinct future data needs:

1. a licensed, revision-aware corporate-action source for scalable negative
   assertions and split/dividend/distribution completeness; and
2. point-in-time event evidence for interpreting discontinuities and later
   strategy/event-risk controls without claiming causality.

The explicit VISN distribution validates the existing decision to keep total
return separate from split-only adjustment. The unresolved DFNS case remains
in review. The other 13 flags remain event-context observations, not resolved
causal labels or proof that split coverage is complete.

## Safety

This review used public, read-only sources and current ticker/exchange values
only as search locators. It did not download or persist source payloads, write
`/data`, contact Massive, change canonical data, run analytics, publish a
Snapshot, build or deploy a bundle, or change a timer/scheduler.
