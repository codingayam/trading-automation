# Congress-Mirror Development Rationale & Launch Readiness

## High-Level Delivery Philosophy
- **Parallelizable tracks with shared foundations:** The project splits into six coordinated groups so that foundational tooling (Group 01) unlocks schema, integrations, and UI delivery without creating long serial chains.
- **Service-aligned ownership:** Tasks mirror the two runtime surfaces (worker + web) and supporting infrastructure, reducing cross-team handoffs during active development.
- **Integration-first thinking:** Early emphasis on Alpaca + Quiver clients and Prisma repositories ensures downstream teams build against real contracts, minimizing rework late in the cycle.
- **Operational readiness baked in:** Deployment, cron scheduling, and observability are planned as their own group to avoid the “last mile” scramble after features appear complete.

## Group Interplay Overview
1. **Foundation / Environment / Shared Clients (G01)**
   - Establishes pnpm workspace monorepo, shared TypeScript config, and env validation.
   - Outputs logging/fetch utilities consumed by every subsequent group.
2. **Database / Prisma / Migrations (G02)**
   - Provides schema + repositories underpinning order submission, ingestion, and dashboard queries.
   - Enables fixture data for UI testing before live integrations are ready.
3. **Alpaca Integration / Trade Support (G03)**
   - Supplies hardened order submission + polling logic that the worker and dashboard reuse.
   - Encodes risk guardrails, ensuring compliance knobs exist before cron automation starts.
4. **Quiver Worker / Job Execution (G04)**
   - Orchestrates ingestion → trade submission → reconciliation loops using outputs from G02 and G03.
   - Maintains checkpoints/job runs so deployment can be idempotent and self-healing.
5. **Dashboard / API / Views (G05)**
   - Presents trading activity and live Alpaca metrics; leverages G02 repositories and G03 clients.
   - Provides visibility for QA to validate end-to-end behaviour during dry runs.
6. **Deployment / Railway / Observability (G06)**
   - Builds Railway automation, cron wiring, and alerting to move from dev to reliable operations.

## Dependency Ladder
- **G01 ⇒ G02 ⇒ G03/G05 ⇒ G04 ⇒ G06** establishes the minimum sequence; however, G03 and G05 can run in parallel once G02 stabilizes.
- Shared package publishing (G01) must be finalized before Prisma client generation (G02) is shared; agree on versioning strategy (e.g. workspace references).
- Alpaca client contracts (G03) should freeze before G04’s worker QA cycle; adopt semantic version bumps when introducing breaking changes.
- G05’s API routes rely on consistent repository interfaces; coordinate release notes from G02 with UI team.

## Risk Posture & Mitigations
- **Integration instability:** Capture Quiver/Alpaca fixtures during early spikes so tests remain deterministic in CI.
- **Cron execution drift:** Worker includes once-per-day guard + explicit logging; Group 06 adds alerting on missed runs.
- **Schema churn:** Define migration approval process; annotate risky changes with rollout plans in repository README.
- **Operational blind spots:** Ensure each critical workflow (fetch, order submit, poll, checkpoint update) emits structured logs and metrics before deployment sign-off.

## Launch Readiness Gates
1. **Foundation Verified** – pnpm workspace commands (`pnpm install`, `pnpm run lint`, `pnpm run test`) succeed; env validation fails fast on missing secrets.
2. **Data Layer Certified** – Prisma migrations apply cleanly in staging; repository tests cover uniqueness + transactional guarantees.
3. **Integration Confidence** – Alpaca fallback logic proven against sandbox; risk guardrails toggle correctly. Quiver ingestion handles pagination/time windows as per spec.
4. **Workflow Dry-Run** – Worker processes seeded day-in-life scenario, producing expected trade + checkpoint records without manual intervention.
5. **Dashboard QA** – Overview/trades/positions pages load against mock and live endpoints with acceptable performance and accessible UI.
6. **Ops Sign-Off** – Railway staging deploy replicates production topology, cron triggers observed, alerts wired to agreed channels, runbooks published.

## Pre-Work Confirmation Checklist
- [x] **Package Manager & Repo Layout** – pnpm monorepo confirmed.
- [x] **CI/CD Strategy** – Hybrid: GitHub Actions handles lint/test/migration checks; successful runs trigger Railway deploys that build/run services.
- [x] **Credential Provisioning** – Runtime secrets stored in Railway environments (staging + prod); manage distribution via Railway secrets management.
- [x] **Staging Infrastructure** – Dedicated Railway environment with isolated Postgres, `TRADING_ENABLED=false`, Alpaca paper endpoints, cron enabled for dry runs.
- [x] **Exchange Calendar Source** – Use Alpaca `/v2/clock` and `/v2/calendar` APIs as canonical; derive ET calculations with `America/New_York` timezone utilities.
- [x] **Alerting Channels** – Plan optional Lark webhook alerts for worker failures/critical notifications (may land post-MVP) alongside baseline logging.
- [x] **Data Retention Decisions** – Retain ledger-oriented tables indefinitely; document backup expectations accordingly.

## Communication Cadence
- Weekly integration checkpoint led by PM to review cross-group blockers, metrics, and readiness gates.
- Async status updates posted in shared channel at minimum twice per week; include testing coverage + outstanding risks.
- Design reviews scheduled ahead of major interface freezes (G02 schema, G03 client, G05 API responses) with stakeholders from dependent groups.

## Next Actions
1. Secure outstanding confirmations from the checklist above.
2. Kick off Group 01 sprint with updated pnpm assumptions and distribute onboarding doc.
3. Prepare fixture capture plan for Alpaca and Quiver to unblock integration testing during network downtime.
4. Align ops + engineering on deployment verification steps to streamline Group 06 execution, including Lark webhook configuration (even if post-MVP) and Railway secrets rotation expectations.
