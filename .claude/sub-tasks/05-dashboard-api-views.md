# Group 05 – Dashboard / API / Views

## Objective
Implement the Next.js dashboard pages and supporting API routes that surface live Alpaca data and persisted trade history to end users.

## Workstreams & Tasks
- Build `/overview` page that queries Alpaca account + positions via revalidated fetch (60s), computes portfolio metrics (`total_unrealized_pl`, `total_cost_basis`, `total_plpc`), and renders charts (Recharts/Chart.js).
- Develop `/trades` page backed by an internal API route that pages through `trade` data, displays status/fill columns, and supports basic filtering by ticker/date.
- Implement `/positions` page that surfaces real-time Alpaca positions without DB writes, reusing Group 03’s client wrapper.
- Introduce a shared UI component library (table, metric cards, status badges) to keep styling consistent and accessible.
- Secure API routes (even if public) with simple request validation and rate limiting to prevent accidental overuse.
- Add unit/component tests (React Testing Library) and integration tests for the API routes (Next.js request handlers) using seeded DB data.
- Ensure pages handle empty states (no trades yet) and error states (Alpaca outage) with user-friendly messaging.

## Acceptance Criteria
- `pnpm run test` covers page rendering logic and API handlers with mocked Alpaca responses.
- Dashboard reflects live Alpaca metrics when credentials are configured; offline mode uses seed data without crashing.
- Pages meet basic performance and accessibility checks (Lighthouse or Next.js built-in analyzer).
- API routes share Prisma repositories and Alpaca client instances via dependency injection, avoiding duplicate connections.

## Dependencies & Preconditions
- Depends on Group 01 for Next.js skeleton and shared UI tooling (distributed via pnpm workspace packages).
- Requires Group 02 for Prisma client/data access and Group 03 for Alpaca client methods.
- Needs trade/job seed data from Group 02 (or worker output) for development/testing.

## Effort & Staffing
- Estimated complexity: Medium (M). 1 frontend engineer and 0.5 backend engineer for 3-4 days.

## External Dependencies / Blockers
- Alpaca rate limits and CORS; plan to proxy requests through Next.js API routes.

## Risks & Mitigations
- **Risk:** Live Alpaca latency slows page loads → **Mitigation:** rely on Next.js cache + optimistic UI updates.
- **Risk:** Table rendering overwhelms clients with many trades → **Mitigation:** use pagination/virtualization if counts exceed expectations; monitor.

## Handoffs & Integration Points
- Consumes outputs from Groups 02–04; coordinate on API contracts and repository exposures.
- Provides observable metrics (front-end logs) to Group 06 for inclusion in operational dashboards.
