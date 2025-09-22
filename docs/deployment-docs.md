# Railway Deployment Playbook

This guide captures the agreed Railway workflow for the Congress‑Mirror project. Two application services live in the monorepo (`apps/web`, `apps/worker`), each with its own `railway.json` config-as-code file. Railway reconciles those files on every deploy, so changes stay versioned alongside the app code.

## Layout
- `apps/web/railway.json` – web service config (install/build/start/healthcheck, Prisma pre-deploy).
- `apps/worker/railway.json` – worker service config (install/build/start, Prisma pre-deploy, cron schedule).
- Postgres is managed via `railway add -d postgres -s postgres`; no manifest is required because Railway handles the plugin directly.

## Bootstrapping a Project
1. Authenticate: `railway login`.
2. Link the repo to the project/environment (run from repo root): `railway link -p congress-mirror -e staging` (repeat for `production` when ready).
3. Ensure the Postgres plugin exists: `railway add -d postgres -s postgres` (no-op if already attached).
4. Deploy each service from its folder so Railway reads the matching `railway.json`:
   ```bash
   railway up -s web         -e staging ./apps/web
   railway up -s worker-open -e staging ./apps/worker
   ```
   `railway up` will create the services if they do not yet exist and sync all settings from the JSON files, including the worker cron (`30 13,14 * * 1-5` UTC).

> **CI/CD usage:** GitHub Actions (or another pipeline) should run `railway up --ci -s <service> -e <env> <path>` after lint/test/migration checks pass. The `--ci` flag streams build logs then exits, matching Railway’s docs.

## Build, Start & Cron Definitions
- **Web (`apps/web/railway.json`)**
  - Install: `pnpm install --frozen-lockfile`
  - Pre-deploy: `pnpm run prisma:generate`, `pnpm run migrate`
  - Build: `pnpm --filter @trading-automation/web run build`
  - Start: `pnpm --filter @trading-automation/web run start`
  - Healthcheck: `/api/health`
- **Worker (`apps/worker/railway.json`)**
  - Install: `pnpm install --frozen-lockfile`
  - Pre-deploy: `pnpm run prisma:generate`, `pnpm run migrate`
  - Build: `pnpm --filter @trading-automation/worker run build`
  - Start: `pnpm open-job`
  - Cron: `30 13,14 * * 1-5` (Railway executes the start command at both UTC times; if a run is still active, the next trigger is skipped, so the worker must complete quickly.)

## Prisma Migrations
Both service manifests use `deploy.preDeployCommand` to run:
1. `pnpm install --frozen-lockfile`
2. `pnpm run prisma:generate`
3. `pnpm run migrate`

These commands execute between build and start. Any failure aborts the deploy, ensuring schema drift is caught before traffic shifts.

## Environment Variables & Secrets
Use config-as-code for non-secret defaults and the CLI for secrets. Example:

```bash
railway variables -e staging -s worker-open --set "DATABASE_URL=postgresql://..."
railway variables -e staging -s web         --set "ALPACA_KEY_ID=..."
railway variables -e staging -s web         --set "ALPACA_SECRET_KEY=..."
```

- Include the same keys in the production environment once staging validation is complete.
- Rotate values via `railway variables` or the dashboard; see `docs/operations.md` for the full procedure.

## Dry-Run Verification
1. In staging, set `TRADING_ENABLED=false` and `PAPER_TRADING=true` so trades do not fire.
2. Trigger the worker manually: `railway run -s worker-open -e staging -- pnpm open-job -- --dry-run`.
3. Review worker logs: `railway logs -s worker-open -e staging` to confirm Alpaca clock/calendar gating and once-per-day skip behavior.
4. Open the staging domain to ensure the dashboard renders and calls succeed.

## Rollback Expectations
- **Application code:** Use the Railway dashboard (Deployments tab → three-dot menu → Rollback) to revert to a previous container image. The CLI does not expose `deploy --rollback`.
- **Database:** If a migration misfires, craft a fix-forward migration or request a point-in-time restore from Railway Postgres support. Do **not** manually edit schema in production.

See `docs/operations.md` for incident handling, cron troubleshooting, and release checklists.
