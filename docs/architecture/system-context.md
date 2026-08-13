# System Context

## Confirmed Logical Flow

```text
Market Data
-> Data Processing
-> Market Structure Analysis
-> Web Presentation
```

## Workstation Responsibility

The workstation is responsible for:

- source repository
- ingestion
- cleaning
- calculations
- historical storage
- scheduled/background computation

## OCI Responsibility

OCI is responsible for:

- whalpha.com
- HTTPS
- Nginx
- lightweight Web/API serving

OCI should not become the primary heavy-compute or historical-data node.

## Browser Responsibility

The browser provides the visual dashboard and calls the Web/API boundary. It must not hold direct data-provider credentials or IBKR credentials.

## Confirmed Non-Goal

The current architecture is not a microservice architecture.

## Accepted Application Stack

The accepted application stack is documented in [ADR 0005](../decisions/0005-application-technology-stack.md) and [Application Architecture](application-architecture.md). The backend and frontend frameworks are selected for the target scaffold.

## Unknown

The exact database introduction threshold and deployment mechanism are not yet selected.
