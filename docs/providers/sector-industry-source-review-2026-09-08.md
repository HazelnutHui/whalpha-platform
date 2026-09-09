# Sector / Industry Source Review — 2026-09-08

## Result

`SOURCE_AUDIT_COMPLETE`

`NO_SOURCE_SELECTED_OR_ACQUIRED`

`GICS_HISTORY_FIRST_SAMPLE_CANDIDATE`

Current display and historical research require different evidence gates. A
latest classification can improve today's product after coverage and identity
validation, but it cannot be projected backward into a backtest.

This review used repository evidence and official public product material. It
did not access an account, credential, endpoint, sample, quote, licensed data,
Git remote, OCI, or Production website.

## Repository facts at audit start

- Canonical Identity contains active status, CIK, FIGIs, currency, locale,
  market, name, exchange, ticker, provider type, and update time. It contains
  no formal Sector, Industry, SIC, market-cap, or taxonomy-history field.
- The implemented Massive adapter supports Instrument Master and EOD bars.
  The bulk All Tickers response used by Instrument Master has no SIC hierarchy.
- Classification V1 was then an accepted logical contract without a Python
  model, persistence layer, formal reader, canonical partition, or Production
  use. The later same-day implementation status is recorded below.
- Sector ETF Rotation is a fixed price-proxy relationship layer. It is not
  security-level Sector/Industry membership.

## Official-source comparison

| Source | Officially documented capability | Main limitation for WH Alpha | Disposition |
| --- | --- | --- | --- |
| [Massive Ticker Overview](https://massive.com/docs/rest/stocks/tickers/ticker-overview) | Single-ticker details include CIK, FIGIs, market cap, SIC code/description, and a `date` query; daily update; Basic has two years and paid individual plans advertise all history | It is one request per ticker; SIC is a coarse filer-oriented classification, not the accepted four-level hierarchy. The endpoint says SEC-derived details queried at a report-period date may include a filing submitted later, which is look-ahead for research | Optional current-only SIC coverage diagnostic after a separately bounded entitlement/permission probe; never formal historical research classification |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Filer submissions and XBRL Company Facts, updated through the day, plus nightly bulk files | CIK and SEC SIC classify a filer, not a listed security. Filing-period and filing-availability clocks differ; security-to-filer resolution remains separate | Supporting issuer evidence only; not a sole taxonomy or security-membership source |
| [S&P Global GICS dataset](https://www.marketplace.spglobal.com/en/datasets/gics-(90)) | Four-level company taxonomy matching Sector -> Industry Group -> Industry -> Sub-industry. GICS History advertises active/inactive classifications, history from 1985, significant coverage from 1999, daily delivery, and point-in-time from/thru dates | Licensed commercial data; public material does not establish the exact security/entity identifiers, knowledge-time fields, revisions, WH Alpha display rights, price, or account delivery | Preferred first specification/sample inquiry because the hierarchy matches the accepted canonical path and historical from/thru dates are explicit |
| [LSEG Industry Classifications](https://www.lseg.com/en/data-catalogue/entity/legal-entity-data/industry-classifications) and [quant-research brochure](https://www.lseg.com/content/dam/data-analytics/en_us/documents/brochures/lseg-data-for-quant-research-brochure.pdf) | TRBC has a five-level global hierarchy, history from 1999, daily/intraday refresh, and bulk/API delivery; LSEG also supports GICS and other frameworks | Public material does not fully establish classification knowledge-time, restatement/revision behavior, exact listed-security crosswalk, or licensed shared-display terms | Strong second sample candidate, especially if one delivery can also close later fundamentals/lifecycle gaps |
| [FactSet RBICS](https://insight.factset.com/resources/factset-revere-business-industry-classifications-datafeed) | Six-level operating-footprint taxonomy; Focus is single-sector, Revenue supplies multi-sector revenue exposure, and U.S.-major revenue history is documented from 2012 | Public material reviewed here does not prove that the primary classification history is strict point-in-time knowledge-time data. Company/product exposure is not the same as one formal traditional identity path | Defer as a complementary peer, theme, and revenue-exposure source; do not make it the first traditional taxonomy dependency |

The 2026-09-08 public follow-up confirmed that S&P Marketplace gates both the
GICS sample data and data dictionary behind credentialed sign-in. The public
GICS structure workbook and methodology define the taxonomy but are not a
company-membership sample. The current public methodology also says a license
is required to display, create derivative works from, or distribute a product
or service using GICS or index data. Therefore the next evidence must be a
credentialed sample/specification and written use terms; public hierarchy files
cannot satisfy the sample or permission gate.

GICS, TRBC, RBICS, and SIC are not interchangeable labels. Their hierarchy,
assignment subject, methodology, revision behavior, and history must remain
identifiable in source observations even when mapped to canonical IDs.

## Accepted temporal and identity boundary

Every external observation must distinguish:

- the provider's company/entity or security identifier;
- the canonical stable `instrument_id` resolution and its evidence;
- taxonomy name, hierarchy version, and external code;
- business-effective `valid_from` / `valid_to`;
- `source_available_at`, when the observation was defensibly knowable;
- provider update/revision time and Dell observation time; and
- direct-security versus explicitly issuer-projected assignment.

Ticker and name may create review candidates only. They cannot produce a
positive classification. A provider company classification may be projected
to multiple listed instruments only through a reviewed stable-ID crosswalk;
the projection basis remains visible.

Current-display eligibility requires a completed latest-as-of observation,
stable identity resolution, taxonomy-version mapping, explicit missing count,
and permission for equal guest/credential derived display. It does not require
historical knowledge-time evidence.

Historical-research eligibility additionally requires complete interval and
revision semantics plus `source_available_at <= signal_cutoff`. If availability
cannot be established, the observation is current-display or outcome-context
only. A business-effective date, filing report period, or provider from-date
cannot substitute for knowledge time.

## First commercial sample gate

Request GICS History specifications and a non-production sample first. The
review packet must establish:

1. a coverage manifest for all 1,831 currently activated instruments, with
   returned, not-covered, ambiguous, and multi-security issuer cases explicit;
2. provider entity/security identifiers and a stable crosswalk path using
   FIGI, CIK plus security evidence, or another reviewed identifier—not ticker
   or name alone;
3. hierarchy definitions, taxonomy versions, from/thru dates, availability or
   publication clocks, revision identifiers, correction history, and inactive
   company handling;
4. a historical change sample containing reclassifications and methodology
   changes, not only unchanged current rows;
5. Dell acquisition, canonical retention, derived research, identical
   guest/credential browser/API display, attribution, redistribution, and
   termination/deletion terms; and
6. delivery mechanics, expected volume, update cadence, price, and whether the
   same contract can later cover fundamentals or other required families.

No percentage coverage threshold is invented before the sample shows actual
missingness and where it occurs. Product activation must expose its denominator
and unknown bucket; research activation must fail closed for an ineligible
instrument-session.

### Required field-to-contract evidence

The specification and sample review must map provider fields to Classification
V1 before an adapter is designed. A vendor field name is not accepted as a
canonical definition by itself.

| Evidence family | Minimum sample evidence | Classification V1 destination or decision |
| --- | --- | --- |
| Provider identity | Stable entity ID, security ID when supplied, identifier type, and explicit company-versus-security grain | `source_entity_id`, `source_security_id`, `identity_evidence`, `assignment_basis`; ticker/name-only rows fail positive resolution |
| Taxonomy | Taxonomy name, methodology/version, code, name, and complete Sector -> Industry Group -> Industry -> Sub-industry path | external taxonomy fields plus versioned canonical definitions and parent links |
| Business validity | Inclusive/exclusive semantics for from/thru dates and examples spanning a reclassification | `valid_from` / half-open `valid_to`; ambiguous boundary conversion is quarantined |
| Knowledge time | Provider publication/availability timestamp or a reproducible dated delivery snapshot proving when the row was knowable | `source_available_at` and `knowledge_time_status`; business-effective dates never substitute |
| Revisions | Update/revision identifier, correction/cancellation behavior, and whether earlier deliveries remain reproducible | `provider_updated_at`, `revision_id`, `correction_status`, and supersession links |
| Inactive coverage | Inactive/delisted companies, terminal classification behavior, and retained historical identifiers | explicit coverage decisions; omission is not interpreted as exclusion |
| Security projection | Reviewed crosswalk for multiple share classes, ADRs, and issuer-to-security projection | stable `instrument_id` resolution plus visible `issuer_projected` basis |
| Permission | Dell storage/backup, historical research, derived metrics, identical guest/credential display, attribution, termination, and deletion terms | one effective-dated permission-review fingerprint; unknown use remains denied |
| Delivery | Full and delta mechanics, effective cutoff, pagination/file completeness, correction cadence, and reproducible version identity | immutable source custody and exact request/file manifest before canonical Apply |

The sample must contain or be supplemented with documented examples for an
unchanged active company, a reclassification, a methodology-version change,
an inactive company, a ticker/identifier change, multiple listed securities
for one issuer, and an ADR or other issuer-projected case. A sample that cannot
exercise a category leaves that category unverified; it is not silently marked
passed.

### Role outcomes

- `historical_research_primary`: every mandatory identity, hierarchy,
  interval, knowledge-time, revision, inactive-coverage, delivery, and
  permission gate passes for the reviewed scope.
- `current_display_only`: current identity, taxonomy, coverage, delivery, and
  equal-display permission pass, but defensible historical knowledge time or
  revision evidence is absent.
- `corroborator_only`: useful facts are supplied, but scope or semantics are
  incomplete and require another governed source.
- `rejected`: positive matching depends on ticker/name, revisions are silently
  overwritten, business validity is presented as knowledge time, omissions
  are hidden, or intended retention/use is not permitted.

GICS History remains first in the sample order, not selected. Public material
supports taxonomy depth and from/thru history but does not close knowledge-time,
revision, identifier, delivery-entitlement, permission, or price gates. TRBC
remains the second comparison. No live adapter should be started until one real
sample is assigned one of the roles above.

## Implementation order

1. Implement the provider-neutral Classification V1 source-observation,
   mapping, canonical-membership, persistence, and reader boundary against
   fixtures.
2. Keep the source adapter disabled until a reviewed specification/sample and
   permission decision exist.
3. After a real sample passes, ingest a Dell-only current snapshot first and
   validate stable-ID coverage and quarantine behavior.
4. Add Candidate Sector/Industry distribution and repeated-exposure
   diagnostics only from the completed current reader. Keep unknown visible.
5. Admit history to research only after knowledge-time and revision gates pass.

No current taxonomy, Massive SIC response, ETF proxy, or manually inferred
label is authorized for historical backfill, Candidate reranking, Defensive
Rotation activation, strategy tuning, Snapshot publication, or deployment by
this review.

## Subsequent same-day implementation status

The provider-neutral Classification V1.1 contracts, explicit coverage ledger,
immutable four-Parquet snapshot, completion manifest, and formal reader were
subsequently implemented and exercised only with fixtures under temporary test
roots. The source-selection result above is unchanged: no real source, sample,
license, adapter, `/data` partition, analytics integration, or deployment
exists.
