# Group 03 – Alpaca Integration / Trade Support

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
