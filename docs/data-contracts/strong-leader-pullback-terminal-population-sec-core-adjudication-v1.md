# Strong-Leader Pullback Terminal-Population SEC Core Adjudication V1

## Purpose

`strong-leader-pullback-terminal-population-sec-core-adjudication/1.0`
adjudicates four bounded source-evidence questions for the corrected-population
SCS case: cover identity, issuer transaction completion, listing-termination
reason, and primary common-share consideration structure. It is not a
canonical lifecycle or terminal-outcome report.

## Inputs and binding

The report formally binds the authoritative source plan, complete source
manifest, and form-aware candidate report. The plan must contain one stable-ID
case and the candidate package must contain one Form 25, one Form 15, and one
structured 8-K for the same source chain.

The boundary identity interval begins on the stable ID's last observed EOD
session and ends one day after the provider delist-date candidate. The interval
exists only to test event-time cover identity and explicitly is not full
lifecycle authority.

## Decisions

- `cover_identity` reuses the inline-XBRL CIK+ticker+exchange+common-equity
  resolver with a retained share-class FIGI and forbids ticker-only identity.
- `transaction_event` selects a date only under the registered prioritized,
  unique-date completion rules.
- `termination_reason` requires one bounded Item 3.01 section that explicitly
  links a completed merger/acquisition to a listing or trading action.
- `common_share_consideration` classifies only the bounded primary ordinary-
  share clause and retains election/fractional-share flags.
- `cross_form_reconciliation` binds CIK, Commission file number, Class A Common
  Stock, exchange, Form 25 notice date, cover report date, and completion date.

Every nested decision retains exact source hashes, bounded evidence, decision
reasons, and logical fingerprints.

## Non-authority and custody

The canonical JSON is exclusively written beneath an owner-only
`adjudication=*` directory, atomically published, and formally reread.
Directories are `0700` and the report is `0400`; an exact replay is idempotent.

Four matched source-evidence decisions do not establish a full lifecycle fact,
first/last tradability, legal delisting effectiveness, party identity,
normalized payoff, terminal reference value, execution price, strategy return,
or terminal outcome. Network, credential, `/data`, Historical Coverage,
research admission, Candidate, publication, deployment, and scheduler counters
remain zero.
