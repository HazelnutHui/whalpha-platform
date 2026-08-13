# Classification Boundary

## Purpose

This document defines the accepted classification boundary for Trading Intelligence Platform. It separates formal security identity, thematic membership, and analytical grouping so market structure, theme rotation, and relationship monitoring do not collapse into one ambiguous taxonomy.

## Status

Accepted Boundary — Not Yet Implemented

## Sector / Industry Classification

Sector / Industry Classification is the stable traditional identity path:

```text
Sector
-> Industry Group
-> Industry
-> Sub-industry
```

Uses:

- traditional market treemap
- sector and industry breadth
- sector and industry relative strength
- stable structural comparison

Rules:

- Each security has one primary traditional classification path at a given effective time.
- The system uses canonical internal classification IDs.
- External provider classifications are mapped into canonical internal classifications.
- Vendor fields must not become permanent canonical taxonomy directly.

## Theme Classification

Theme Classification is many-to-many, adjustable, and versioned. A stock may belong to multiple Themes, and Theme membership does not replace formal industry identity.

Examples:

- AI Infrastructure
- Semiconductors
- Optical Networking
- Cloud Software
- Nuclear Energy
- Crypto Infrastructure

Rules:

- Inclusion criteria must be explicit and explainable.
- Initial membership may be curated.
- V1 does not include automatic Theme inference.
- Later changes use effective dating.

## Analytical Groups

Analytical Groups are analysis baskets rather than company identity.

Uses:

- Relative Leadership
- Rotation
- Divergence
- Rolling Correlation
- Relative Performance Spread
- hedging relationships
- relationship regime monitoring

Examples:

- Software vs Semiconductors
- Mega-cap Technology vs Semiconductors
- Growth vs Value
- Large Cap vs Small Cap
- Cyclical vs Defensive

Rules:

- Analytical Group membership does not define official industry identity.
- Construction methodology must be recorded.
- Construction methods may include ETF constituents, curated baskets, or rule-based selection.
- One security may belong to multiple Analytical Groups.
- Automatic relationship discovery remains an open question.

## Membership Semantics

All three classification families require:

- stable internal ID
- source
- methodology version
- valid_from
- valid_to
- review status where applicable

Theme and Analytical Group membership are many-to-many. Traditional industry path is unique at a given effective time.

## Effective Dating

Classification definitions and memberships must preserve history with valid-from and valid-to dates. Historical analytics should use classifications valid for the evaluated time period where practical.

## Provider Mapping Boundary

External provider taxonomies are inputs. Provider Adapters or mapping procedures translate those inputs into canonical internal classifications. Internal calculations should use the canonical classification IDs and should not depend on vendor-specific field names.

## Deferred Automation

Automatic Theme inference and automatic relationship discovery are deferred. V1 can start with curated membership and explicit methodology notes.

## Non-Goals

- final taxonomy vendor selection
- automated Theme inference
- automatic relationship discovery
- investment recommendation labels
- replacing industry identity with Theme labels
- provider adapter implementation
