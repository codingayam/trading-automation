# Development Workflow

Group 01 ships the base tooling needed for every other squad. This quickstart shows how to bootstrap the repo, run both services, and wire secrets from Railway.

## Prerequisites
- Node.js 18.19+
- pnpm 8+
- Postgres instance (local or Railway) for `DATABASE_URL`

## Install & Bootstrap
```bash
pnpm install
```

All workspace scripts are exposed at the root for convenience:

- `pnpm dev` – starts the Next.js app in `apps/web`
- `pnpm open-job` – executes the worker entrypoint once (used by Railway cron)
- `pnpm lint` / `pnpm test` – run linting and Vitest across every package

## Running Both Services Together
1. Create a `.env` by copying `.env.example` and fill in the required secrets (Alpaca + Quiver + Postgres).
2. In one terminal, run the dashboard:
   ```bash
   pnpm --filter web dev
   ```
3. In another terminal, keep the worker hot-reloading for local testing:
   ```bash
   pnpm --filter worker dev
   ```
   The dev script uses `tsx watch` so subsequent edits rerun immediately. The production cron (and local dry runs) always execute `pnpm open-job`.

## Connecting to Railway/Postgres
- Grab the Railway Postgres `DATABASE_URL` and place it in `.env` for both services.
- Railway service variables should mirror `.env.example`; keep Alpaca and Quiver secrets in Railway’s environment tab.
- When running locally against Railway, ensure your IP is allow-listed (if applicable) or use an SSH tunnel.

## Testing & Quality Gates
- `pnpm lint` enforces shared ESLint + Prettier config across apps and packages.
- `pnpm test` runs Vitest with environment-loader coverage to guard against missing env vars.
- Shared utilities (`@trading-automation/shared`) compile via `pnpm --filter @trading-automation/shared build` and are auto-transpiled inside Next.js via `transpilePackages`.

## Deployment Notes
- Railway web service: `pnpm run build` → `pnpm run start`.
- Railway worker service: `pnpm run open-job` as the Start Command; the cron remains `30 13,14 * * 1-5` UTC.
- Before promotion, ensure `pnpm test` and `pnpm lint` pass in CI to satisfy Group 06 handoff.
