# Group 06 – Deployment / Railway / Observability

## Objective
Operationalize the system on Railway with separate web and worker services, cron scheduling, migrations, and baseline monitoring/runbooks.

## Workstreams & Tasks
- Create Railway project configuration (via `railway.json` or CLI) defining `web`, `worker-open`, and `postgres` services with appropriate build/start commands.
- Automate Prisma migrations on deploy using Railway deploy hooks (`pnpm run migrate`) and document rollback procedures.
- Configure the worker service cron schedule (`30 13,14 * * 1-5` UTC) and verify once-per-day protections align with Group 04’s `job_run` logic, including runtime checks against Alpaca `/v2/clock` and `/v2/calendar` before trades fire.
- Set up environment variable management across services (shared vs service-specific) and provide a secrets rotation checklist.
- Implement logging/monitoring exports: structured logs to Railway, optional Lark webhook alerts on non-zero worker exits or missed cron triggers (can land post-MVP), plus any additional webhook integration.
- Draft runbooks covering incident response (e.g. Alpaca outage, Quiver downtime, migration failure) and recovery steps.
- Validate deployment by performing a full dry-run in Railway staging, including dashboard smoke tests and worker execution against sandbox APIs with `TRADING_ENABLED=false`, observing Alpaca clock/calendar gating behaviour.

## Acceptance Criteria
- Railway manifests/scripts checked into repo enable `railway up` (or CI) to provision both services without manual clicks.
- Deploy pipeline runs Prisma migrations automatically (triggered after GitHub Actions CI success) and surfaces failures prominently.
- Alerting is in place for worker failure modes and critical env vars have documentation for rotation/testing.
- Operations runbook is published in `/docs/operations.md` with clear escalation paths and verification checklists.

## Dependencies & Preconditions
- Depends on Groups 01–05 delivering runnable services and tests.
- Requires access to Railway project/org and shared understanding that runtime secrets live in Railway environments (staging/prod).

## Effort & Staffing
- Estimated complexity: Medium (M). 1 DevOps/infra engineer for 3 days with coordination across feature teams.

## External Dependencies / Blockers
- Railway cron availability and pricing; confirm limits before finalizing schedule. Track Lark webhook approvals/config (optional for MVP).
- Need Slack/email integration for alerts (ensure approvals).

## Risks & Mitigations
- **Risk:** Migrations fail in production without rollback plan → **Mitigation:** require manual gating or blue/green strategy for schema changes.
- **Risk:** Missing alerts delay response to failed trades → **Mitigation:** integrate worker summary metrics into dashboards and set error thresholds.

## Handoffs & Integration Points
- Receives build artifacts/tests from earlier groups; coordinates go-live checklist with PM/QA.
- Provides feedback loop to Groups 03–04 on operational metrics for continuous improvements.
