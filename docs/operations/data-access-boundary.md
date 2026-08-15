# Data Access Boundary

## Purpose

This document records the operational access boundary for public placeholder content, public data-free demos, and private provider-backed dashboards.

## Status

Accepted Operational Boundary — Access Control Not Implemented

This is an engineering boundary, not legal advice. Provider terms and permissions must be rechecked before public release or commercial use.

## Public Placeholder

The public development placeholder may include:

- WH Alpha branding
- project description
- development status
- architecture overview
- feature descriptions

It must not include restricted provider Market Data or derived analytics based on restricted provider data.

## Public Data-Free Demo

A public portfolio or dashboard demo may be created later only if it uses:

- clearly marked synthetic/demo fixtures, or
- data with explicit public-display rights

The demo must not imply live or real market state, must not expose credentials, and must remain separated from the private real-data dashboard.

## Private Provider-Backed Dashboard

Any Massive-backed or other restricted provider-backed dashboard must be intended only for the owner until a suitable public-display or redistribution authorization exists.

Required properties:

- effective private access control
- not publicly indexable
- no unrestricted static export containing restricted data
- no unrestricted public API endpoint containing restricted data or derived analytics
- no provider credentials in browser bundles

## Protected API Responses

Any API response containing restricted provider data or derived works must require effective private access control before deployment. API routes that expose provider-backed market state cannot be treated as public placeholder endpoints.

The first private EOD read routes are implemented for local/private development and are default-disabled by `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=false`. Setting this flag to true registers the routes for local verification only. It is not authentication, authorization, or deployment approval.

## Static Export Restrictions

Static exports must not contain restricted provider-backed data, market-state snapshots, heatmaps, analytics, research, or derived works unless appropriate public-display rights are documented.

## Credential Boundary

Provider credentials must remain outside Git and outside frontend bundles. `TIP_MASSIVE_API_KEY` is the accepted environment-variable name for Massive. The real value is provisioned outside Git in the protected workstation credential file and must never be copied into the repository. Real values, account identifiers, tokens, private keys, and unreviewed credential locations must not be recorded in repository documentation, chat, command history, process arguments, or logs.

## OCI Boundary

OCI remains a lightweight public serving layer. It must not receive full raw market-history datasets or unrestricted provider-backed exports. Any provider-backed content deployed through OCI requires the pre-deployment gate below.

## Pre-Deployment Gate

Before any real Massive data or provider-derived works are deployed, all of the following must be complete:

1. Provider terms rechecked.
2. Actual account entitlement verified.
3. Private access-control mechanism selected.
4. Access control implemented.
5. Access control independently verified.
6. No provider credential in frontend bundle.
7. No unrestricted provider-backed API endpoint.
8. Documentation updated.
9. Deployment review completed.

## Incident Rule

If real provider-backed content is accidentally made public:

- stop public serving of the affected content
- preserve logs without exposing credentials
- rotate credentials if exposure is suspected
- document the incident
- re-verify access controls

No incident automation is implemented by this document.

## Non-Goals

- implementing Cloudflare Access
- configuring Nginx Basic Auth
- creating users or credentials
- creating a login page
- modifying whalpha.com
- deploying provider-backed data
- making legal determinations
