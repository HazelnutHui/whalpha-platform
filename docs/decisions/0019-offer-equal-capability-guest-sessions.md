# ADR 0019: Offer Equal-Capability Guest Sessions

## Status

Accepted

## Date

2026-08-26

## Context

WH Alpha is a personal, non-commercial research workspace used by the owner and
a small circle of friends. The existing branded entry requires the one private
credential even though the product policy explicitly requires guests and
signed-in users to see the same data, functionality, language choices,
Universes, precision, and analysis. Creating a role model would add state and
authorization branches without a current product need.

Provider-backed static data must not become an unprotected asset URL. The
existing Nginx `auth_request` boundary and opaque server-side Session are still
useful for origin containment, logout, expiry, and uniform protection of both
the application and its JSON payloads.

## Decision

Add a same-origin `POST /auth/guest` entry that creates the same opaque
server-side Session used by credential login. The Session contains no role,
entitlement, user identity, or capability flag. Both entry paths therefore
pass the identical Nginx authorization check and load the exact same static
Dashboard and private-data files.

The guest endpoint:

- accepts only a JSON `next` value and applies the existing safe Dashboard-path
  validation;
- rejects cross-origin browser requests and unknown fields;
- has Nginx and Auth Service rate limits separate from password-failure state;
- fails closed at a bounded active-Session capacity after first removing expired
  Sessions;
- returns only authentication state and the safe next path;
- sets the existing Secure, HttpOnly, SameSite=Lax, host-only Session cookie;
  and
- never exposes a role or creates an alternative data route.

The entry page must state plainly that guest and credential Sessions receive
the same product. The application utility header calls the result a protected
Session rather than implying a particular identity.

## Consequences

- A visitor can enter without receiving or sharing the owner's password.
- Guest and credential Sessions are intentionally indistinguishable to the
  Dashboard and static data boundary.
- Service restart and seven-day expiry invalidate both kinds of Session.
- This is public entry to a personal prototype, not a general identity system,
  commercial redistribution decision, or promise of anonymous availability.
- A future product decision that introduces private holdings or different
  entitlements must define a new identity and authorization model first; it
  must not silently overload this role-free Session.

## Alternatives Considered

- Publish `/dashboard/` and `/private-data/` without a Session: rejected because
  it removes the uniform application/data boundary and makes later containment
  harder.
- Share the owner's password: rejected because it creates unnecessary secret
  distribution and poor revocation behavior.
- Add guest and member roles now: rejected because current product policy
  forbids content or capability differences and no role-dependent feature is
  authorized.
- Use a third-party identity provider immediately: deferred until the personal
  prototype needs durable identities or per-user private state.

## Non-Goals

- per-user portfolios, watchlists, preferences, or audit history
- role-based data, language, Universe, precision, or feature differences
- automated trading or brokerage access
- changing provider acquisition or data-publication rights

## 2026-08-28 provider compatibility finding

The equal-capability implementation remains an accurate product decision, but
the current official Massive individual-use terms describe Market Data as
owner-only, prohibit an application intended for other end users, and restrict
third-party display of Market Data and Derived Works. Session protection and
non-commercial friend access do not resolve that source-permission gap.

This ADR does not override provider terms. Massive-backed guest/friend use is
blocked as a supported data-source posture until the user obtains compatible
permission/license or selects an alternate display-compatible source. The
finding does not itself authorize disabling guest access, changing payloads,
deleting data, or deploying a replacement.

## 2026-08-28 product-policy reaffirmation

The user explicitly reaffirmed that current guest and credential Sessions must
retain the highest identical shared-product capability. Owner-only or member-
only market analysis is not an acceptable workaround for a source-permission
conflict. A source that cannot support equal-capability serving must remain out
of future shared web publications for both entry paths until permission or a
replacement source is documented. This decision does not alter the currently
deployed payload.

Future personal watchlists, holdings, and brokerage records are a different
content scope: they may be isolated to their owner only after a real user-
identity model exists, while shared market data and analytics remain identical.
