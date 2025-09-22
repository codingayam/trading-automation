# Group 03 – Alpaca Integration / Trade Support

## Status
- ✅ Typed Alpaca REST client with authenticated requests, response parsing, and error mapping for validation/buying power cases
- ✅ `submitTradeForFiling` orchestration covers notional submission, whole-share fallback, guardrails, and polling persistence
- ✅ Risk guardrail enforcement wired to env toggles with structured logging + repository-backed counts
- ✅ Vitest coverage across success, fallback, guardrail block, and insufficient buying power paths
- ✅ `TradeRepository` extended with window counting + Decimal null handling for reconciliation updates

## Key Deliverables
- `packages/shared/src/alpaca/client.ts:1` – resilient Alpaca client sharing orders, account, positions, and latest trade lookups with retry-aware error translation
- `packages/shared/src/alpaca/trade-support.ts:1` – `submitTradeForFiling` transactionally evaluates guardrails, records trades, handles fallback, propagates actionable errors, and triggers status polling
- `packages/shared/src/alpaca/polling.ts:1` – exponential backoff polling loop updating trades until terminal statuses or timeout
- `packages/shared/src/alpaca/guardrails.ts:1` – guard evaluation utilities emitting structured logs + throwable guardrail errors
- `packages/shared/src/alpaca/types.ts:1` & `packages/shared/src/alpaca/status.ts:1` – shared typing + status mapping consumed by worker and dashboards
- `packages/shared/src/db/repositories/trade-repository.ts:17` – new `countTradesInWindow` helper and Decimal coercion tweaks supporting guard counts + fallback nullification
- Env surface extended with `ALPACA_DATA_BASE_URL` (`packages/shared/src/env.ts:215`, `.env.example:12`) to target market data API for fallback pricing
- Fixture pack under `packages/shared/fixtures/` with canonical Alpaca + Quiver payloads for worker integration tests

## Testing
- `pnpm --filter @trading-automation/shared test` (Vitest) exercises Alpaca trade support happy path, fallback, guardrail disablement, and insufficient buying power failure using Prismock-backed repositories

## Follow-ups
- [ ] Align with Group 04 on worker wiring (e.g., provide trading window boundaries + logger injection) and end-to-end job orchestration
- [ ] Evaluate rate-limit handling once Alpaca sandbox connectivity is available; extend client retry policy if real responses surface additional codes
- [ ] Consider capturing Alpaca `request_id` when moving off `httpFetch` to aid production diagnostics

## Objective
Build a resilient Alpaca client and trading support layer that submits notional orders, applies guardrails, and reconciles fill status as defined in the PRD.

## Workstreams & Tasks
- Implement a typed Alpaca REST client (orders, positions, account) with retry/backoff and auth headers sourced from the shared env loader.
- Develop order submission helpers that prioritize notional orders (`notional=1000`), detect 422 responses, and gracefully fall back to whole-share orders using latest trade price.
- Encode risk guardrails driven by env vars (`DAILY_MAX_FILINGS`, `PER_TICKER_DAILY_MAX`, `TRADING_ENABLED`, `PAPER_TRADING`) with metrics/logging when guards block execution.
- Create a polling module that checks order status for up to 1 minute with exponential backoff, updating `trade.status`, `filled_qty`, `filled_avg_price`, and timestamps.
- Integrate error handling for insufficient buying power, fractional restrictions, and network timeouts, surfacing actionable errors back to the worker.
- Write unit/integration tests using Alpaca sandbox/mocks to validate fallback logic, guardrails, and status transitions.

## Acceptance Criteria
- A single entry point (e.g. `submitTradeForFiling()`) executes the full notional→fallback flow and returns a structured result consumed by the worker.
- Polling updates are persisted via the repositories from Group 02, and retries stop once terminal statuses are reached or timeout hits.
- Risk guard decisions are logged with structured context (ticker, filing_date) and can be toggled via env vars without code changes.
- Test suite covers success, fallback, guardrail block, and error scenarios.

## Dependencies & Preconditions
- Requires Group 01 for shared env/logging utilities (delivered via pnpm workspace shared packages) and Group 02 for Prisma repositories.
- Needs Alpaca API credentials (paper trading) and access to Alpaca sample code for reference; sandbox network access must be coordinated.

## Effort & Staffing
- Estimated complexity: Medium (M). 1 backend engineer full-time for ~3 days with QA support for mock testing.

## External Dependencies / Blockers
- Dependence on Alpaca paper trading availability limits full end-to-end testing; plan for sandbox outages.

## Risks & Mitigations
- **Risk:** Alpaca API rate limits during polling → **Mitigation:** implement adaptive backoff and consolidate polling when multiple orders are outstanding.
- **Risk:** Fallback quantity rounding issues → **Mitigation:** add unit tests around edge tickers (high price/low liquidity) using captured fixtures.

## Handoffs & Integration Points
- Supplies `submitTradeForFiling` and polling hooks consumed by Group 04’s worker orchestration.
- Exposes lightweight client methods (`getPositions`, `getAccount`) that Group 05 uses for dashboard data fetching.
