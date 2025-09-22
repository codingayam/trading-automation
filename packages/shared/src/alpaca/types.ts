export type AlpacaOrderStatus =
  | 'new'
  | 'accepted'
  | 'partially_filled'
  | 'filled'
  | 'canceled'
  | 'pending_new'
  | 'pending_cancel'
  | 'rejected'
  | 'expired'
  | 'stopped'
  | 'suspended'
  | 'calculated';

export interface AlpacaOrder {
  id: string;
  client_order_id: string;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  filled_at: string | null;
  expired_at: string | null;
  canceled_at: string | null;
  failed_at: string | null;
  replaced_at: string | null;
  replaced_by: string | null;
  replaces: string | null;
  asset_id: string;
  symbol: string;
  asset_class: string;
  notional: string | null;
  qty: string | null;
  filled_qty: string;
  filled_avg_price: string | null;
  order_class: string;
  order_type: string;
  type: string;
  side: string;
  time_in_force: string;
  limit_price: string | null;
  stop_price: string | null;
  status: AlpacaOrderStatus;
  extended_hours: boolean;
  legs: AlpacaOrder[] | null;
  trail_percent: string | null;
  trail_price: string | null;
  hwm: string | null;
  subtag: string | null;
  source: string | null;
  position_intent?: string | null;
  expires_at?: string | null;
}

export interface SubmitAlpacaOrderRequest {
  symbol: string;
  side: 'buy' | 'sell';
  type?: 'market' | 'limit' | 'stop' | 'stop_limit' | 'trailing_stop';
  time_in_force?: 'day' | 'gtc' | 'opg' | 'cls' | 'ioc' | 'fok';
  notional?: string;
  qty?: string;
  client_order_id?: string;
  extended_hours?: boolean;
}

export interface AlpacaAccount {
  id: string;
  status: string;
  currency: string;
  buying_power: string;
  regt_buying_power: string;
  daytrading_buying_power: string;
  cash: string;
  portfolio_value: string;
  pattern_day_trader: boolean;
  trading_blocked: boolean;
  transfers_blocked: boolean;
  account_blocked: boolean;
  crypto_status: string;
  shorting_enabled: boolean;
  long_market_value: string;
  short_market_value: string;
  initial_margin: string;
  maintenance_margin: string;
  last_equity: string;
  last_maintenance_margin: string;
  sma: string;
}

export interface AlpacaPosition {
  asset_id: string;
  symbol: string;
  exchange: string;
  asset_class: string;
  asset_marginable: boolean;
  qty: string;
  avg_entry_price: string;
  side: 'long' | 'short';
  market_value: string;
  cost_basis: string;
  unrealized_pl: string;
  unrealized_plpc: string;
  unrealized_intraday_pl: string;
  unrealized_intraday_plpc: string;
  current_price: string;
  lastday_price: string;
  change_today: string;
  qty_available?: string;
}

export interface AlpacaErrorResponse {
  code?: string | number;
  message?: string;
  data?: unknown;
}

export interface AlpacaLatestTradeResponse {
  symbol: string;
  trade: {
    t: string;
    price: number;
    size: number;
    exchange: string;
    conditions?: string[];
  };
}

export interface AlpacaClock {
  timestamp: string;
  is_open: boolean;
  next_open: string;
  next_close: string;
}

export interface AlpacaCalendarEntry {
  date: string;
  open: string;
  close: string;
  session_open?: string | null;
  session_close?: string | null;
}

export interface GuardrailConfig {
  tradingEnabled: boolean;
  paperTrading: boolean;
  tradeNotionalUsd: number;
  dailyMaxFilings?: number;
  perTickerDailyMax?: number;
}

export interface GuardrailContext {
  tradingDateWindowStart: Date;
  tradingDateWindowEnd: Date;
  ticker: string;
  tradesSubmittedToday: number;
  tradesSubmittedTodayForTicker: number;
}

export type GuardrailDecision =
  | { allowed: true }
  | {
      allowed: false;
      guard: string;
      message: string;
      context?: Record<string, unknown>;
    };

export interface SubmitTradeResult {
  tradeId: string;
  alpacaOrderId?: string;
  clientOrderId?: string;
  status: TradeStatus | 'failed';
  guardrailBlocked?: boolean;
  fallbackUsed?: boolean;
  notionalSubmitted?: string | null;
  qtySubmitted?: string;
}
import type { TradeStatus } from '@prisma/client';
