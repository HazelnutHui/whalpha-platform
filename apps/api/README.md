# Trading Intelligence API

FastAPI backend scaffold for Trading Intelligence Platform.

## Purpose

The API provides typed contracts for the future dashboard. The current scaffold only proves the API boundary and versioned routing shape.

## Current Endpoint

- `GET /api/v1/health`

Expected response:

```json
{
  "status": "ok",
  "service": "trading-intelligence-api",
  "version": "0.1.0"
}
```

## Local Setup

Use the repository-level instructions in [Local Development](../../docs/development/local-development.md).

## Current Non-Goals

- No market data provider integration
- No database or ORM
- No authentication
- No order execution
- No production deployment configuration
