# Railway Deployment Playbook

This folder contains the infrastructure-as-code definition for Railway along with the automation hook that applies Prisma migrations during deploys.

## Layout
- `railway.json` – primary manifest consumed by `railway up`.
- `hooks/postdeploy.sh` – executed after successful builds to ensure Prisma client generation and migrations run before traffic is served.

## Bootstrapping a Project
1. Authenticate with Railway: `railway login`.
2. From the repo root, create or select the project: `railway use --project congress-mirror` (name can be overridden in `railway.json`).
3. Apply the manifest: `railway up --service web --service worker-open --environment staging`.
4. Provision the Postgres plugin by running `railway plugins apply --service postgres` if it does not exist automatically.
5. Confirm the cron schedule is attached to `worker-open` with `railway cron list`. The manifest encodes `30 13,14 * * 1-5` UTC to mirror NYSE opens across DST.

> **Headless usage:** In CI/CD call `railway up --ci --environment staging` (or `production`) after the pipeline artifacts are built. The command is idempotent and reconciles any drift in service configuration.

## Build & Start Commands
- **Web**
  - Install: `pnpm install --frozen-lockfile`
  - Build: `pnpm --filter @trading-automation/web run build`
  - Start: `pnpm --filter @trading-automation/web run start`
  - Healthcheck: `/api/health`
- **Worker (`worker-open`)**
  - Install: `pnpm install --frozen-lockfile`
  - Build: `pnpm --filter @trading-automation/worker run build`
  - Start: `pnpm open-job`
  - Cron: `30 13,14 * * 1-5`

## Applying Prisma Migrations
Deploys trigger `deploy/railway/hooks/postdeploy.sh`, which performs:
1. `pnpm install --frozen-lockfile`
2. `pnpm run prisma:generate`
3. `pnpm run migrate`

If any step fails the deploy aborts. The script is safe to re-run and can be executed manually for diagnostics:

```bash
./deploy/railway/hooks/postdeploy.sh
```

## Environment Variables
The manifest defines variable groups used across environments:
- `shared-db` – Prisma pool settings.
- `alpaca` – API base URLs (keys are injected per-environment in Railway).
- `quiver` – Base URL override.
- `web-only` – Web-specific public config.
- `worker-only` – Worker guardrails (`TRADE_NOTIONAL_USD`, caps).

Secrets (`ALPACA_KEY_ID`, `ALPACA_SECRET_KEY`, `QUIVER_API_KEY`, `DATABASE_URL`, etc.) are **not** committed. Set them via `railway variables set --environment <env> <key>=<value>` or the dashboard. See `docs/operations.md` for the rotation checklist.

## Dry-Run Verification
For staging smoke tests after a deploy:
1. Set `TRADING_ENABLED=false` and `PAPER_TRADING=true` in the staging environment.
2. Trigger the worker manually using `railway run worker-open -- pnpm open-job -- --dry-run`.
3. Inspect logs with `railway logs --service worker-open` to confirm Alpaca clock/calendar gating works.
4. Navigate to the staging web domain and confirm the dashboard renders using live Alpaca paper positions.

## Rollback Strategy
- Database schema: use `pnpm migrate:dev` locally to craft fix-forward migrations. The Postgres plugin retains physical backups; request a point-in-time restore from the Railway dashboard if an irreversible migration lands.
- Application: `railway deploy --service web --rollback` (or `worker-open`) restores the previous container image.

See `docs/operations.md` for expanded incident response procedures.
