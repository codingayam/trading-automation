# Group 01 – Foundation / Environment / Shared Clients

## Objective
Establish the project scaffolding, shared tooling, and configuration patterns that enable the worker and web services to develop against a consistent TypeScript/Prisma stack.

## Workstreams & Tasks
- Define repository structure (pnpm workspace monorepo with `apps/web`, `apps/worker`, `packages/shared`) and baseline scripts (`dev`, `build`, `lint`, `test`).
- Configure TypeScript project references, ESLint/Prettier, Husky (optional), and Jest/Vitest test harnesses for both services.
- Implement a shared environment loader (zod-based) that validates required variables for local/dev/prod; author `.env.example`.
- Add shared utilities for logging (pino or winston), HTTP fetch wrapper with retry/backoff, and a centralized error type.
- Stub the worker entrypoint (`pnpm run open-job`) and Next.js app shell so downstream groups can plug in logic without structural changes.
- Document local development workflow, including how to run services concurrently and how to point to Railway/Postgres from local.

## Acceptance Criteria
- Running `pnpm install` followed by `pnpm run lint` and `pnpm run test` succeeds on a clean checkout.
- `pnpm run dev` starts the Next.js shell; `pnpm run open-job` executes a no-op worker with structured logging.
- `.env.example` lists all variables referenced in the PRD, grouped by service, and the runtime throws on missing vars.
- Shared logging + fetch utilities are published in `packages/shared` and consumed by both services without circular dependencies.

## Dependencies & Preconditions
- None; this is the first execution group. Ensure stakeholders are aligned on the pnpm workspace structure before implementation.

## Effort & Staffing
- Estimated complexity: Medium (M). Expect 1 full-stack engineer for 2-3 days with occasional infra consultation.

## External Dependencies / Blockers
- Decision confirmed: pnpm workspace monorepo; CI runs via GitHub Actions with deploy handoff to Railway after green checks.

## Risks & Mitigations
- **Risk:** Divergent service configs later on → **Mitigation:** enforce shared tsconfig/eslint via workspace root.
- **Risk:** Missing env vars discovered late → **Mitigation:** integrate env validation into startup with unit tests covering required vars.

## Handoffs & Integration Points
- Unblocks Group 02 for Prisma schema work and Group 03 for API client development by delivering shared utilities and validated configs.
- Provide a short onboarding doc/checklist in `/docs/` summarizing scripts and service layout for downstream teams.

## Status – 2025-09-22
- ✅ pnpm workspace scaffolded with `apps/web`, `apps/worker`, and `packages/shared`; root scripts (`dev`, `build`, `lint`, `test`, `open-job`) fan out to package-level commands.
- ✅ TypeScript project references, shared ESLint/Prettier config, and Vitest harness wired across packages; worker exposes a `dev` watch command for local loops.
- ✅ Shared package publishes env loader (Zod), Pino-based logger factory, retrying `httpFetch`, and typed error helpers; unit tests cover env validation coercions.
- ✅ `.env.example` enumerates Alpaca, Quiver, and guardrail knobs; runtime env parsing throws on missing/invalid values.
- ✅ Worker entry (`pnpm open-job`) emits structured no-op logs; Next.js shell (App Router) and `/api/health` route consume shared utilities and serve as UI skeleton.
- ✅ Authored `docs/development-workflow.md` detailing local setup, concurrent service runs, and Railway/Postgres integration notes.
- ✅ `pnpm lint` and `pnpm test` execute cleanly after config updates (lint still surfaces expected Next.js informational warnings). `pnpm install` may require direct registry access when run inside the sandbox.
