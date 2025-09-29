## Potential sources of error
- DATABASE_URL & DIRECT_DATABASE_URL are all the same url from Postgres (Railway)
- Hybrid CI/CD not implemented: ideally CI will trigger lint, type, and other tests before using railway up for CD. 
- No monitoring/alerting infra (Slack/Lark webhooks)

## Local checks
pnpm lint / pnpm run lint
pnpm test / pnpm run test
pnpm run lint && pnpm exec tsc --noEmit
pnpm --filter web dev
pnpm --filter worker dev

lots of other things to be run found in /package.json
e.g. pnpm build etc..

## e2e dry run for cron job
railway run --service worker-open -- pnpm test:e2e

## Deployment
- 2 services: (1) /apps/web and (2) /apps/worker. The first is for the dashboard and related logic; second for cron job 
- DEPLOY FROM ROOT: (currently using staging environment)
1. railway up -s web -e staging
2. railway up -s worker-open -e staging