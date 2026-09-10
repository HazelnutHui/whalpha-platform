# System Context

## Confirmed Logical Flow

```text
Market Data
-> Data Processing
-> Market Structure Analysis
-> Quantitative Research and Falsification
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
- bounded AI-assisted research orchestration

## OCI Responsibility

OCI is responsible for:

- whalpha.com
- HTTPS
- Nginx
- lightweight Web/API serving

OCI must not become the primary heavy-compute, research-orchestration, or
historical-data node.

## Browser Responsibility

The browser provides the visual dashboard and calls the Web/API boundary. It must not hold direct data-provider credentials or IBKR credentials.

## Confirmed Non-Goal

The current architecture is not a microservice architecture.

## Accepted Application Stack

The accepted application stack is documented in [ADR 0005](../decisions/0005-application-technology-stack.md) and [Application Architecture](application-architecture.md). The backend and frontend frameworks are selected for the target scaffold.

## Open architecture threshold

The static OCI deployment mechanism is selected and operational. A database
introduction threshold remains open and must be justified by measured query,
concurrency, state, or recovery requirements rather than scale expectations.
