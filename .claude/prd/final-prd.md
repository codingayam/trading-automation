Congress‑Mirror Automated Trading System (High‑Level MVP Spec)

Goal: Each trading day at U.S. market open (9:30am ET), ingest every individual Congress BUY filing (no dedup), place a separate $1,000 BUY per filing via Alpaca, record trades, and show a dashboard. No sells, no auth, no webhooks. Portfolio performance is computed on each page load using Alpaca /v2/positions.

⸻

1) Architecture Overview
	•	Two Railway services + Postgres:
	1.	Worker (open job) – a tiny Node/TS service with Start Command pnpm run open-job. Railway Cron triggers this service at 13:30 and 14:30 UTC (DST/STD). It does not expose HTTP.
	2.	Web/API – Next.js app for dashboard + optional read-only API routes. No cron attached here.
	•	Postgres (Railway managed) – system of record (trades, filings, job runs). No scheduled snapshots required.
	•	Data sources – Quiver (disclosures), Alpaca (orders + live positions/account for performance).

[Quiver] --> [Worker: open-job (BUY per filing)] --> [Postgres]
                                            \--> [Alpaca Orders + short polling] --> [Postgres]

[Next.js Web/API (pages + server routes)] <-------------------------------> [Alpaca positions/account]
                                         <-------------------------------> [Postgres]
                                     (computes P&L on request using Alpaca)

———————————––> [Postgres]
(computes P&L on request using yfinance)

---

## 2) Tech Stack (lean)
- **Worker & Web:** Node.js (TypeScript)
- **Framework:** Next.js (App Router or Pages)
- **DB/ORM:** Postgres + Prisma
- **UI:** Next.js + React + Recharts/Chart.js
- **Deployment:** Railway (**1 Worker service with Cron + 1 Web service + Postgres**)
- **Package Manager:** pnpm workspace monorepo (`apps/web`, `apps/worker`, `packages/shared`)

---

## 3) Minimal Data Model
- **congress_trade_feed**
  - `id` (PK), `ticker` (from Quiver `Ticker`), `member_name` (from Quiver `Name`), `transaction` (from Quiver `Transaction` - raw string stated as Purchase, we change to BUY), `trade_date` (from Quiver `Traded`), `filing_date` (from Quiver `Filed`), `party` (from Quiver `Party`), `raw_json` (JSONB), `ingested_at`

- **trade** *(one row per filing we attempted to execute)*
  - `id` (PK)
  - `source_hash` (UNIQUE; deterministic hash of `Name|Ticker|Filed|Transaction`)
  - `client_order_id` (indexed)
  - `id` (response from POST from creating new order)
  - `symbol` (ticker)
  - `side` (enum: BUY)
  - `order_type` (enum: market)
  - `time_in_force` (enum: day)
  - `notional_submitted` (DECIMAL)  ← `$1,000` target when fractional/notional is allowed
  - `qty_submitted` (DECIMAL)       ← populated when falling back to whole shares, should be ignored by default when order_type = market
  - `filled_qty` (DECIMAL)
  - `filled_avg_price` (DECIMAL)
  - `status` (accepted/new/partially_filled/filled/canceled/rejected/failed)
  - `created_at`, `submitted_at`, `updated_at`, `filled_at`, `canceled_at`, `failed_at`
  - `raw_order_json` (JSONB)
- **job_run**
  - `id` (PK), `type` (`open-job`), `trading_date_et` (DATE), `status`, `started_at`, `finished_at`, `summary_json`
  - **UNIQUE** (`type`, `trading_date_et`) to enforce once‑per‑day
- **ingest_checkpoint** *(high‑water mark for Quiver `Filed`)*
  - `trading_date_et` (PK, DATE), `last_filed_ts_processed_et` (TIMESTAMPTZ), `updated_at`

> We do **not** maintain a local `position` table for correctness; live positions come from Alpaca.

---

## 4) Strategy & Execution (MVP rules)
- **No dedup:** If 3 members buy AMZN today, submit **3 separate BUYs**.
- **Fixed sizing:** `$1,000` **per filing**.
  - **Preferred:** submit a **notional order** (`notional="1000"`). Default order_type is "market"
  - **Auto‑fallback:** if fractionals are off or Alpaca returns 422 validation, compute whole shares: `qty = floor(1000 / last_trade_price)` and submit standard share order. If `qty == 0` or insufficient BP → **skip & log**.
- "order_type"=Market, "time_in_force"=day.
- **Reconcile:** After submission, **poll** Alpaca for 1 minute with backoff; update `trade.{status, filled_qty, filled_avg_price, filled_at}`.
- **High‑water mark ingestion (next‑open rule):**
  - At **9:30 ET**, trade **yesterday’s filings after your last run up to 23:59 ET**, **plus today’s filings up to 09:30 ET**.
  - Store `last_filed_ts_processed_et` per `trading_date_et` so **today 09:31–23:59 ET** will be picked up **tomorrow at open**.
- **Risk guards (env‑configurable):** optional per‑ticker/day caps and a daily max filings cap.

---

## 5) Scheduled Jobs (Railway Cron)
**Cron attaches to the Worker service only**; Railway runs the Worker's **Start Command**.

- **Worker (open‑job)**
- **Start Command:** `pnpm run open-job`
  - **Cron:** `30 13,14 * * 1-5` (UTC) → covers DST/Standard Time; job itself enforces once/day via `job_run` and checks Alpaca's GET /v2/clock and GET /v2/calendar as the source of truth to decide if run on 13.30 or 14.30 UTC.
- **Flow (high‑water mark windows in ET):**
    1. Compute `today_et`, `prev_trading_day_et`, and `open_ts_et = today 09:30:00`.
    2. Query Alpaca `/v2/clock` and `/v2/calendar` to confirm the market is open today and whether this invocation (13:30 vs 14:30 UTC) should execute or exit early.
    3. **Backfill prev day:** fetch Quiver `date=prev_trading_day_et`; trade rows with `Filed_et > last_filed_ts_processed_et(prev)`.
    4. **Trade today pre‑open:** fetch Quiver `date=today_et`; trade rows with `Filed_et ≤ open_ts_et`.
    5. Submit `$1,000` notional orders (fallback to whole shares on 422); insert `trade` rows; **poll** and update.
    6. Update checkpoints: set `last_filed_ts_processed_et(prev) = end_of_day(prev)` and `last_filed_ts_processed_et(today) = open_ts_et`.

> **No EOD snapshot cron.** The dashboard computes performance live from Alpaca on each request (cached ~60s in Next.js).

---

## 6) Dashboard (Next.js)
- **/overview:** Live portfolio view from **Alpaca**:
  - `GET /v2/positions` →
    - `total_unrealized_pl = Σ unrealized_pl`
    - `total_cost_basis = Σ cost_basis`
    - `total_plpc = total_unrealized_pl / total_cost_basis`
  - Wrap both calls with **Next.js Data Cache**: `fetch(url, { next: { revalidate: 60 } })`.
- **/trades:** Table of all trades and fill status (per filing) from our DB.
- **/positions:** Render live Alpaca response (no DB write required).

---

## 7) Deployment on Railway
- **Services**
  - **web** (Next.js): Build `pnpm run build` → Start `pnpm run start`. **No cron** attached.
  - **worker-open** (Node/TS): Start `pnpm run open-job`. **Cron:** `30 13,14 * * 1-5`.
  - **postgres**: Railway managed.
- **Deploy Command (both services):** `pnpm run migrate` (Prisma migrate deploy). Triggered after GitHub Actions CI (lint/tests/migration check) succeeds; safe to run every deploy.
- **Env Vars (shared where needed):**

DATABASE_URL=
ALPACA_KEY_ID=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets
QUIVER_API_KEY=
PAPER_TRADING=true
TRADING_ENABLED=true
TRADE_NOTIONAL_USD=1000          # fixed $ per filing
DAILY_MAX_FILINGS=200            # optional safety cap
PER_TICKER_DAILY_MAX=25          # optional safety cap per symbol

---

## 8) Delivery Plan & Parallel Workstreams

### Grouping Rationale
- Split work into six groups to isolate foundation, data, trading, ingestion, UI, and deployment concerns, matching natural service boundaries (worker vs web) and external integrations (Alpaca, Quiver, Railway).
- Database schema (Group 02) is independent once the workspace is ready, enabling simultaneous progress with Alpaca integration (Group 03) while the worker orchestration (Group 04) waits for both to stabilize.
- Dashboard build (Group 05) can advance in parallel with worker development by relying on seeded data and shared Alpaca client utilities, accelerating UI feedback without blocking backend delivery.
- Deployment/ops (Group 06) is sequenced last to consume stable artifacts from earlier groups while codifying cron/alerting requirements highlighted in the PRD.

### Recommended Development Sequence
1. **Group 01 – Foundation / Environment / Shared Clients**: establish repo, tooling, env validation, and stubs to unblock all subsequent streams.
2. **Group 02 – Database / Prisma / Migrations**: deliver schema + repositories so integrations and UI can build against real data models.
3. **Group 03 – Alpaca Integration / Trade Support**: implement order + polling logic; share clients for both worker and dashboard.
4. **Group 04 – Quiver Worker / Job Execution**: assemble ingestion + execution pipeline leveraging Groups 02–03 outputs.
5. **Group 05 – Dashboard / API / Views**: build Next.js pages/API atop repos and Alpaca client while worker testing continues.
6. **Group 06 – Deployment / Railway / Observability**: finalize infrastructure, cron, migrations, and operational runbooks once services pass acceptance.

### Dependency Highlights
- Group 02 depends on Group 01’s shared tooling; Groups 03–05 depend on Group 02’s Prisma client and seed data.
- Group 03 supplies Alpaca client methods consumed downstream by Groups 04 and 05; coordinate interface changes via shared package versioning.
- Group 04 requires stable Quiver API access and relies on Group 03’s trade helper for consistent error handling; ensure combined testing in staging prior to launch.
- Group 05 consumes both DB and Alpaca data; mock responses early to avoid blocking on worker completion.
- Group 06 aggregates outputs from all prior groups; align on deployment checklist once Groups 01–05 finish primary QA.

### Coordination & Next Steps
- Broadcast confirmed pnpm monorepo decision so Group 01 can cement workspace scaffolding and scripts.
- Secure Alpaca (paper) and Quiver API credentials; manage via Railway environment secrets so Groups 03–05 can validate integrations, and capture optional Lark alert webhook configuration alongside secret handoffs (post-MVP if time constrained).
- Schedule joint design reviews between Groups 02 & 03 (data access + trading flows) and Groups 04 & 05 (API contracts/data shapes).
- Establish weekly integration checkpoint to review worker run logs, dashboard status, and deployment readiness; involve ops once Group 04 hits end-to-end testing.

### Assumptions & Open Questions
- Decision locked: pnpm workspace monorepo; surface any compliance requirements that would force repo split ASAP.
- Presumes Alpaca paper trading environment is accessible during development; identify fallback plan if network restrictions apply.
- Requires confirmation of Quiver API rate limits and pagination behaviour to size caching/fixture strategy for Group 04.
- Deployment plan expects Railway-managed Postgres and cron availability as described; verify service quotas before final scheduling and track Lark webhook approval (optional for MVP).

### Supporting Artifacts
- `.claude/docs/development-rationale.md` – end-to-end delivery rationale, sequencing logic, and pre-flight confirmation checklist (reflects CI/CD hybrid model, secrets strategy, staging setup, optional Lark alerting plan, and ledger retention).
