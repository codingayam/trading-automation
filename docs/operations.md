# Operations Runbook – Congress-Mirror

This runbook summarizes day-2 operations for the trading automation system deployed on Railway.

## On-Call Checklist
- Monitor Railway deploys for `web` and `worker-open`; failed builds or post-deploy hooks block traffic.
- Review daily worker runs around 13:30 and 14:30 UTC. Expect exactly one successful execution per trading day (the second cron run should log `skipped`).
- Confirm dashboard availability via the `/api/health` endpoint. Railway’s healthcheck monitors it automatically.

## Environment & Secrets Management
### Core Secrets
| Key | Scope | Rotation Notes |
| --- | --- | --- |
| `DATABASE_URL` | Both services | Rotate via Railway Postgres connection reset. Update `DIRECT_DATABASE_URL` if connection pooling toggles. |
| `ALPACA_KEY_ID` / `ALPACA_SECRET_KEY` | Worker + web Server Actions | Regenerate in Alpaca dashboard. Set new pair in Railway, toggle `TRADING_ENABLED=false`, run smoke tests, then re-enable. |
| `QUIVER_API_KEY` | Worker | Generate via Quiver account. Test ingestion in staging before promoting. |

### Rotation Procedure
1. Stage changes in the non-production environment first.
2. For secrets shared across services, use `railway variables set --environment <env> --service web KEY=VALUE` and repeat for `worker-open`, or rely on variable groups defined in `railway.json`.
3. Trigger `railway up --environment <env>` so new settings materialize in the deployment.
4. Run smoke tests (dashboard, manual worker dry-run).
5. Promote values to production once staging succeeds.

Document each rotation in the team changelog with timestamp, operator, and validation evidence.

## Cron & Worker Monitoring
- Railway surfaces cron execution status under the `worker-open` service. Enable email/webhook alerts for failed or skipped runs.
- Worker logs summarize:
  - `clock` + `calendar` payload to confirm Alpaca trading window.
  - Filing window stats (counts, duplicates, guardrail blocks).
  - Trade submission summary.
- On failure, rerun manually with `railway run worker-open -- pnpm open-job -- --dry-run` to validate config without trading.

### Missed Cron Trigger
1. Check Railway cron history; if no invocation occurred, manually run the worker.
2. Inspect `job_run` table to verify once-per-day logic did not block execution. Run inside Railway shell:
   ```bash
   railway run web -- pnpm exec prisma db pull
   railway run web -- pnpm exec prisma studio
   ```
   or connect via `psql` using the Postgres plugin credentials.
3. Confirm cron schedule in `railway.json` remains `30 13,14 * * 1-5`. Re-apply manifest if drift occurred: `railway up --environment production`.

## Migration Failures
1. The deploy hook stops the rollout; services remain on the previous version.
2. Download migration logs from Railway and reproduce locally with `pnpm migrate:dev`.
3. Craft a fix-forward migration. Avoid manual schema edits in production.
4. Re-run deployment. For reparative action, you can execute the hook manually: `railway run web -- ./deploy/railway/hooks/postdeploy.sh`.
5. If a destructive migration landed, request a Railway point-in-time restore for the Postgres plugin; coordinate downtime with stakeholders.

## Third-Party Outages
### Alpaca API
- Expected symptom: worker aborts after clock/calendar check or order submission fails with 5xx/gateway timeout.
- Mitigation: job exits with failure; hold trades until Alpaca stabilizes. Manual override is not recommended unless Alpaca confirms markets are open.
- Action: notify business stakeholders, monitor Alpaca status page, rerun worker once service resumes.

### Quiver API
- Symptom: ingestion errors or empty filing windows.
- Mitigation: worker logs capture HTTP status + error body. Keep `TRADING_ENABLED=false` until ingestion is healthy to avoid trading stale data.
- Action: escalate to data provider, consider seeding filings manually if outage exceeds one trading day.

## Dashboard Issues
- Healthcheck path `/api/health` should return 200. If it fails:
  1. Inspect logs: `railway logs --service web`.
  2. Validate Prisma connectivity by running `railway run web -- pnpm exec prisma migrate status`.
  3. If CPU/memory throttling occurs, scale `numReplicas` or size via `railway scale`.

## Deployment Verification (Per Release)
1. Confirm CI passed (`pnpm lint`, `pnpm test`).
2. Deploy to staging with `railway up --environment staging`.
3. Run worker in dry-run mode (`TRADING_ENABLED=false`, `--dry-run`).
4. Launch dashboard smoke test (positions list renders, no console errors).
5. Flip staging `TRADING_ENABLED=true` when ready for paper trades; keep production off until go-live.
6. Promote to production via `railway up --environment production`. Monitor first cron execution.

## Escalation
- Primary: Infra on-call (Group 06) – respond within 30 minutes during trading days.
- Secondary: Group 04 (worker pipeline) for ingestion/trade logic regressions.
- Trading halts or compliance concerns escalate to Product Owner immediately.
