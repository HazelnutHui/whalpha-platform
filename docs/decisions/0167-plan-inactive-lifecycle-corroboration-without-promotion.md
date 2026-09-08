# ADR 0167: Plan inactive lifecycle corroboration without promotion

- Status: Accepted
- Date: 2026-09-08

## Context

ADR 0148 produced a complete, disconnected resolution shadow for the
2026-09-03 inactive-source anchor. Of 23,469 source observations, 547 pass the
strict stable-identity, source-ticker-history, candidate-date, and no-later-
canonical-observation gates. They are still only review candidates. The
inactive provider row does not prove a last tradable session, terminal reason,
successor, consideration, or historical source-availability time.

The 547 candidates are 547 unique canonical instruments. Their provider
exchange locator distribution is 271 XNAS and 276 across ARCX, BATS, XASE, and
XNYS. Nasdaq Daily List is a documented candidate source for Nasdaq events,
but no pilot or completeness proof exists. No all-exchange composition has
been selected for the other venues. The provider `last_updated_utc` field is
present for all candidates, but its semantics have not been established as a
defensible market-knowledge timestamp.

Promoting the candidates now would convert absence of contradiction into
positive lifecycle evidence and introduce look-ahead risk.

## Decision

Add an offline corroboration-plan boundary that formally rereads the exact
shadow and writes one immutable, owner-only JSON plan below `/tmp`.

Each review work item binds:

- the source occurrence and complete shadow-decision fingerprints;
- the canonical `instrument_id`, candidate effective date, canonical observed
  bounds, and provider exchange locator;
- explicit requirements for effective-date corroboration, last tradable
  session, terminal classification, successor/consideration applicability,
  and source-availability semantics; and
- a required-but-unexecuted canonical EOD terminal-path cross-check.

The plan does not copy ticker, name, or provider stable-ID values. The provider
exchange is locator-only and cannot establish a fact. XNAS rows route to a
bounded Nasdaq Daily List pilot requirement; all other rows remain blocked on
all-exchange source selection. The route never claims that Nasdaq Daily List
is sufficient.

Every row remains `first_observed_only`, carries no `source_available_at`, and
is ineligible for point-in-time signals. The provider last-updated field is
recorded only as present or absent with
`unverified_not_source_availability` semantics.

The plan is created atomically without overwrite and formally reread by
physical hash and logical fingerprint. It has zero network, `/data`,
analytics, publication, deployment, or scheduler authority. It does not
authorize acquisition, canonical lifecycle Apply, Historical Coverage, or
performance evaluation.

## Consequences

- The 547 candidates become an exact, deduplicated review queue rather than an
  informal aggregate.
- Source selection and representative pilots can be scoped by venue without
  using ticker as a positive join.
- A provider revision timestamp cannot silently become historical knowledge
  time.
- Canonical lifecycle remains absent until separately acquired evidence is
  normalized, permission-reviewed, resolved under a family-specific policy,
  and applied through a separately reviewed path.
- The next transition is source review and bounded pilot design, not bulk
  acquisition or candidate promotion.
