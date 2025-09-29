# Testing Coverage Overview

## Unit Tests

### Implemented
- `packages/shared/src/time/__tests__/time.test.ts` – Exercises date helpers to ensure we interpret Quiver filings in Eastern time.
- `packages/shared/src/env.test.ts` – Validates worker/web/shared env schemas.
- `apps/web/components/ui/__tests__/ui-components.test.tsx` – Verifies shared UI primitives via jsdom.
- `apps/worker/src/__tests__/open-job-runner.helpers.test.ts` – Locks ticker/member normalization and filing window date collection.

### Planned
- None currently.

## Contract Tests

### Implemented
- `packages/shared/src/quiver/__tests__/client.test.ts` – Confirms auth headers, failure handling, and malformed payload logging for Quiver.
- `packages/shared/src/alpaca/__tests__/client.test.ts` – Confirms Alpaca REST headers and retry behaviour on transient 5xx responses.

### Planned
- None currently.

## Integration Tests

### Implemented
- `packages/shared/src/db/repositories/__tests__/trade-repository.test.ts` – Covers Prisma repository persistence.
- `packages/shared/src/alpaca/__tests__/trade-support.test.ts` – Exercises `submitTradeForFiling` against mocked Alpaca flows.
- `apps/worker/src/__tests__/open-job-runner.integration.test.ts` – Exercises the open-job pipeline, including re-runs on the same trading date and late Quiver filings.
- `apps/web/app/api/*/*.test.ts` – Verifies API route responses.

### Planned
- None currently.

## End-to-End Tests

### Implemented
- `tests/e2e/run-worker-dry-run.js` – Executes the worker entrypoint with `--dry-run`, using live Quiver/Alpaca credentials to smoke connectivity without placing orders.
- `tests/e2e/dashboard-healthcheck.js` – Hits the deployed `/api/health` endpoint when `E2E_HEALTHCHECK_URL` is provided.

### Planned
- Automate `pnpm test:e2e` in CI/Railway so smokes run on schedule (currently manual).

> **Note:** `pnpm test` executes every package’s test script by way of the workspace filters, so the same Vitest files may appear multiple times in the output even though they are listed once here for clarity.
