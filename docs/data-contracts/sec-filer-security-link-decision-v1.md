# SEC Filer-to-Security Link Decision V1

## Purpose and grain

`sec-filer-security-link-decision/1.0` is a derived daily decision family. It
contains one row for every canonical Instrument Master row in every included
session and records whether that stable security has one defensible SEC filer
CIK link.

It is not an issuer master, a ticker history, a lifecycle fact, or permission
to project filer-level fundamentals onto a security.

## Row fields

Each row contains:

- session date and stable `instrument_id`;
- effective display ticker and canonical instrument type;
- normalized SEC CIK and `sec-cik:<ten digits>` filer key when admitted;
- decision status and deterministic reason codes;
- count of resolved Provider Identity source occurrences supporting the row;
- same-session instrument count for the selected CIK;
- source Identity knowledge class and actual source-observed timestamp where
  applicable;
- exact source-row-set fingerprint; and
- `issuer_projection_authorized=false`.

Decision statuses are:

- `admitted_unique_cik`;
- `quarantined_missing_cik`;
- `quarantined_conflicting_cik`; and
- `quarantined_identity_mismatch`.

One CIK supporting more than one instrument does not change an admitted link
to quarantine. `cik_instrument_count` makes the one-to-many relationship
visible so a later feature layer can apply an explicit share-class policy.

## Daily source reconciliation

For each session the source inventory binds the exact manifest and Parquet
SHA-256 values for:

- Instrument Master;
- Provider Instrument Identity; and
- Provider Identity Reference Observation.

The Identity source manifest must bind the same canonical Instrument and
Provider Identity fingerprints. Every Instrument Master row must receive one
decision. Resolved Provider Identity rows must reconcile to the corresponding
stable instrument. Unresolved, ambiguous, excluded, and rejected source counts
remain explicit in the build manifest.

## Time and admission

`as_of_date` is the relationship's effective observation date.
`source_observed_at` is when Dell actually acquired the bound provider source.
`point_in_time_eligibility` is copied exactly from source custody:

- `outcome_reconciliation_only`; or
- `eligible_at_source_observed_at`.

The link builder never backdates knowledge. Downstream research must evaluate
the retained eligibility state against its signal cutoff.

## Physical and authority boundary

Daily Parquet artifacts are immutable, deterministically ordered by
`instrument_id`, and initially written below an explicit owner-only Dell
candidate root. A completion manifest binds the exact session index, all
source and output hashes, schemas, counts, conflict distributions, code
revision, and content fingerprint.

The candidate has zero canonical-write, Membership, analytics, publication,
deployment, scheduler, fundamental-projection, and performance authority.
