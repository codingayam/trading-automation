-- CreateEnum
CREATE TYPE "CongressTradeTransaction" AS ENUM ('BUY', 'SELL', 'UNKNOWN');

-- CreateEnum
CREATE TYPE "CongressParty" AS ENUM ('DEMOCRAT', 'REPUBLICAN', 'INDEPENDENT', 'OTHER', 'UNKNOWN');

-- CreateEnum
CREATE TYPE "TradeSide" AS ENUM ('BUY');

-- CreateEnum
CREATE TYPE "TradeOrderType" AS ENUM ('MARKET');

-- CreateEnum
CREATE TYPE "TradeTimeInForce" AS ENUM ('DAY');

-- CreateEnum
CREATE TYPE "TradeStatus" AS ENUM ('NEW', 'ACCEPTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'REJECTED', 'FAILED');

-- CreateEnum
CREATE TYPE "JobRunType" AS ENUM ('OPEN_JOB');

-- CreateEnum
CREATE TYPE "JobRunStatus" AS ENUM ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED');

-- CreateTable
CREATE TABLE "congress_trade_feed" (
    "id" TEXT NOT NULL,
    "ticker" TEXT NOT NULL,
    "member_name" TEXT NOT NULL,
    "transaction" "CongressTradeTransaction" NOT NULL,
    "trade_date" TIMESTAMP(3) NOT NULL,
    "filing_date" TIMESTAMP(3) NOT NULL,
    "party" "CongressParty",
    "raw_json" JSONB NOT NULL,
    "ingested_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "congress_trade_feed_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "trade" (
    "id" TEXT NOT NULL,
    "source_hash" TEXT NOT NULL,
    "client_order_id" TEXT,
    "alpaca_order_id" TEXT,
    "symbol" TEXT NOT NULL,
    "side" "TradeSide" NOT NULL DEFAULT 'BUY',
    "order_type" "TradeOrderType" NOT NULL DEFAULT 'MARKET',
    "time_in_force" "TradeTimeInForce" NOT NULL DEFAULT 'DAY',
    "notional_submitted" DECIMAL(18,2),
    "qty_submitted" DECIMAL(18,6),
    "filled_qty" DECIMAL(18,6),
    "filled_avg_price" DECIMAL(18,6),
    "status" "TradeStatus" NOT NULL DEFAULT 'NEW',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "submitted_at" TIMESTAMP(3),
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "filled_at" TIMESTAMP(3),
    "canceled_at" TIMESTAMP(3),
    "failed_at" TIMESTAMP(3),
    "raw_order_json" JSONB,
    "congress_trade_feed_id" TEXT,

    CONSTRAINT "trade_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "job_run" (
    "id" TEXT NOT NULL,
    "type" "JobRunType" NOT NULL DEFAULT 'OPEN_JOB',
    "trading_date_et" DATE NOT NULL,
    "status" "JobRunStatus" NOT NULL DEFAULT 'PENDING',
    "started_at" TIMESTAMP(3),
    "finished_at" TIMESTAMP(3),
    "summary_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "job_run_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ingest_checkpoint" (
    "trading_date_et" DATE NOT NULL,
    "last_filed_ts_processed_et" TIMESTAMP(3),
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ingest_checkpoint_pkey" PRIMARY KEY ("trading_date_et")
);

-- CreateIndex
CREATE INDEX "congress_trade_feed_ticker_idx" ON "congress_trade_feed"("ticker");

-- CreateIndex
CREATE INDEX "congress_trade_feed_filing_date_idx" ON "congress_trade_feed"("filing_date");

-- CreateIndex
CREATE UNIQUE INDEX "trade_source_hash_key" ON "trade"("source_hash");

-- CreateIndex
CREATE UNIQUE INDEX "trade_alpaca_order_id_key" ON "trade"("alpaca_order_id");

-- CreateIndex
CREATE INDEX "trade_client_order_id_idx" ON "trade"("client_order_id");

-- CreateIndex
CREATE UNIQUE INDEX "job_run_type_trading_date_et_key" ON "job_run"("type", "trading_date_et");

-- AddForeignKey
ALTER TABLE "trade" ADD CONSTRAINT "trade_congress_trade_feed_id_fkey" FOREIGN KEY ("congress_trade_feed_id") REFERENCES "congress_trade_feed"("id") ON DELETE SET NULL ON UPDATE CASCADE;

