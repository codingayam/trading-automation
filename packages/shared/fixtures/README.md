# Shared Fixture Index

Deterministic JSON payloads usable by the worker integration test harness.

## Alpaca (`packages/shared/fixtures/alpaca`)
- `order-notional-accepted.json` – canonical response from `POST /v2/orders` when a $1,000 notional order is accepted.
- `order-filled.json` – terminal polling snapshot for the same order once fully filled.
- `order-validation-422.json` – body returned with HTTP 422 when notional orders are rejected because fractionals are disabled.
- `latest-trade-aapl.json` – sample from `GET /v2/stocks/{symbol}/trades/latest` used for fallback quantity sizing.
- `clock-open.json` – `GET /v2/clock` response indicating the market is open at 09:30 ET.
- `calendar-2024-02-16.json` – `GET /v2/calendar?start=2024-02-16&end=2024-02-16` response covering a regular trading session.

## Quiver (`packages/shared/fixtures/quiver`)
- `congresstrading-2024-02-15.json` – primary happy-path day with three BUY filings (including a high-priced ticker to trigger whole-share fallback logic).
- `congresstrading-2024-02-16.json` – mixed day including SELL + malformed entries to exercise worker filtering/guard rails.

Fixtures mirror the shapes returned by the live services so Group04 can plug them into mocks without additional transforms.
