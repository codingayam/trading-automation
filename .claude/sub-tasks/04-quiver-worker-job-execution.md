# Group 04 – Quiver Worker / Job Execution

## Objective
Deliver the end-to-end worker responsible for ingesting Quiver filings at market open, executing trades via Alpaca, and maintaining ingestion checkpoints and job run records.

## Workstreams & Tasks
- Implement the `pnpm run open-job` entrypoint that orchestrates the cron-triggered workflow, including structured startup logs and graceful shutdown. On start, query Alpaca `/v2/clock` and `/v2/calendar` to validate trading session and decide whether to execute the run (13:30 vs 14:30 UTC).
- Integrate Quiver API client (leveraging provided sample code) to fetch filings for `prev_trading_day_et` and `today_et` windows, respecting high-water mark checkpoints.
- Persist raw filings into `congress_trade_feed`, generate deterministic `source_hash` values, and ensure duplicates are ignored at the DB layer while still recording trade attempts.
- For each eligible filing, invoke Group 03’s trade helper, create `trade` records, and collect execution telemetry (success/failure, fallback path, guard blocks).
- Maintain `job_run` records with once-per-day enforcement, including summary JSON capturing counts, error details, Alpaca clock metadata, and next checkpoint values.
- Update `ingest_checkpoint` before exit (prev day → end_of_day; today → open_ts) only after successful completion, with rollback/compensation on failure.
- Add metrics/logging for critical stages (fetch counts, orders submitted, Alpaca poll outcomes, Alpaca clock/calendar responses) and surface failure signals via exit codes for Railway alerting.
- Provide integration tests or high-level mocks that cover: no filings, filings requiring fallback orders, guard-rail skips, and checkpoint persistence.

## Acceptance Criteria
- Running the worker against seeded data results in correct DB state transitions (filings stored, trades recorded, checkpoints advanced) matching PRD rules, including honoring Alpaca `/v2/clock` downtime windows.
- Job aborts early if another `job_run` exists for the day, logging the reason without duplicating work.
- Failures during Quiver fetch or Alpaca submission are captured in `job_run.summary_json` and cause non-zero exit codes, enabling reruns.
- The worker can be executed locally with CLI flags for dry-run (no Alpaca order submission) to assist QA.

## Dependencies & Preconditions
- Depends on Groups 01–03 for pnpm workspace scaffolding, Prisma repositories, and Alpaca integration.
- Requires Quiver API key and clarity on rate limits; coordinate with ops for quotas.

## Effort & Staffing
- Estimated complexity: Large (L). Recommend 2 backend engineers pairing over ~5 days (one focused on orchestration, one on resilience/testing).

## External Dependencies / Blockers
- Quiver API latency/availability; consider capturing fixture data for offline testing.
- Need deterministic exchange calendar utility (e.g. `market-hours` library) to compute `prev_trading_day_et` accurately.

## Risks & Mitigations
- **Risk:** Partial failures leave inconsistent checkpoints → **Mitigation:** wrap checkpoint updates in transactions and write compensating logic for replays.
- **Risk:** Cron overlap or delayed execution → **Mitigation:** enforce idempotent `job_run` checks and log start/finish times for observability.

## Handoffs & Integration Points
- Produces DB data consumed by Group 05’s dashboard.
- Shares run summaries with Group 06 for alerting/operational dashboards.
