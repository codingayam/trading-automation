# Group 02 – Database / Prisma / Migrations

## Status
- ✅ Prisma schema, enums, and migrations implemented (`packages/shared/prisma/schema.prisma`, migration `20240220100000_initial`)
- ✅ Root and shared package scripts for `migrate`, `prisma:generate`, `seed`; Prisma pinned to `6.16.2`
- ✅ Shared Prisma client wrapper + pooling options (`packages/shared/src/db/client.ts`) and transaction helper
- ✅ Repository layer covering trade, job run, ingest checkpoint, and congress feed datasets with unique constraint handling
- ✅ Seed script with representative Quiver + Alpaca fixtures (`packages/shared/prisma/seed.ts`)
- ✅ Vitest coverage using Prismock in-memory PrismaClient mock; unique constraint error mapped to `UniqueConstraintViolationError`
- 🚧 Documentation sync with Group 03 on repository APIs (in progress, awaiting their interface sketch)

## Key Deliverables
- `packages/shared/prisma/schema.prisma` mirrors PRD “Minimal Data Model”, including enums for trade/job states and JSONB columns.
- Initial SQL migration under `packages/shared/prisma/migrations/20240220100000_initial/` with indexes + unique constraints (`trade.source_hash`, `trade.alpaca_order_id`, `job_run (type,trading_date_et)`).
- Environment validation extended to Prisma toggles (pool mode, connection/timeouts, logging).
- `packages/shared/src/db` exports:
  - `client.ts` shared Prisma client with pool param support and optional query logging.
  - `transactions.ts` helper for consistent transactional execution.
  - Repository classes (`trade`, `job-run`, `ingest-checkpoint`, `congress-trade-feed`) normalising Decimal inputs and rethrowing Prisma P2002 as domain error.
  - `prisma-errors.ts` utilities + `UniqueConstraintViolationError` surfaced via shared index.
- Seed + pnpm scripts (`pnpm run seed`, package-level `prisma:seed`) populate demo trades/job runs for downstream teams.
- Tests (`packages/shared/src/db/repositories/__tests__/trade-repository.test.ts`) exercise Prismock-backed repositories and assert unique constraint mapping.

## Runbook / Commands
- Generate client: `pnpm prisma:generate` (root) or `pnpm --filter @trading-automation/shared run prisma:generate`
- Apply migrations locally: `pnpm migrate:dev`
- Deploy migrations (Railway): `pnpm migrate`
- Seed development data: `pnpm run seed`
- Package-only workflows (`packages/shared`): `pnpm --filter @trading-automation/shared run <script>`

## Follow-ups
- [ ] Align with Group 03 on repository method signatures (e.g. trade reconciliation transactions).
- [ ] Expand test suite to cover job run + checkpoint repositories once consumer usage patterns land.
- [ ] Prepare fixture loader for Group 05 once dashboard query needs surface (likely extend current seed script).
