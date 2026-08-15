# ADR 0012: Use Server-Side Sessions for the Private Dashboard

## Status

Accepted

## Date

2026-08-15

## Context

The first private Dashboard deployment used browser-native Basic Auth. It protected `/dashboard/` and `/private-data/`, but the browser dialog could not provide the WH Alpha branded login experience, explanatory copy, or controlled error handling that the user requested.

The private Dashboard is still a personal prototype. OCI should remain a lightweight web-serving plane, and the Dashboard should continue to consume static derived JSON snapshots rather than running the market-data API on OCI.

## Decision

Replace browser-native Basic Auth prompts with a branded public `/login/` page and a minimal server-side session Auth Service.

The Auth Service:

- listens only on `127.0.0.1`
- reads the existing htpasswd file as the server-side credential store
- validates the single configured user without logging passwords or hashes
- creates opaque random in-memory sessions
- sets a `__Host-whalpha_session` cookie with `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, and no `Domain`
- expires sessions after seven days
- invalidates all sessions on service restart
- supports logout by deleting the current session
- applies a small login rate limit

Nginx uses `auth_request` for `/dashboard/` and `/private-data/`. Unauthenticated Dashboard requests redirect to `/login/?next=/dashboard/`; unauthenticated private JSON requests return 401. `/auth/internal-verify` is an internal Nginx subrequest location and is not publicly callable.

## Consequences

- The user gets a professional WH Alpha login page instead of a browser-native Basic Auth popup.
- Dashboard authentication state is represented by an opaque server-side session, not by JavaScript-stored credentials.
- No database is required for V1; service restart invalidates sessions.
- The existing htpasswd file remains the credential store, but it is no longer exposed through browser-native Basic Auth.
- Authenticated visual verification still requires the user to enter the password in their browser. Codex must not know or use the password.

## Alternatives Considered

- Keep browser Basic Auth: rejected because it cannot provide the requested branded login flow or controlled error handling.
- Store credentials or tokens in frontend storage: rejected because credentials must remain server-side.
- Add a database-backed identity system: deferred as unnecessary for the personal prototype.
- Use Cloudflare Access or OIDC immediately: deferred as a future stronger access-control option.

## Non-Goals

- multi-user identity management
- password reset or account administration
- storing sessions in a database
- exposing private data publicly
- changing Massive credentials or market-data ingestion

## Login submission clarification

The branded login page uses JavaScript to prevent native form navigation and submit a same-origin JSON `POST /auth/login` request. Native form navigation to `/auth/login` is not the accepted user flow because errors must remain on the login page and credentials must never appear in URL state or browser history.
