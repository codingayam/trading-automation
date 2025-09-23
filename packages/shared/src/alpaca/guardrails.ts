import { TradeGuardrailError } from '../errors.js';
import type { Logger } from '../logger.js';
import type { GuardrailConfig, GuardrailContext, GuardrailDecision } from './types.js';

const GUARD_TRADING_DISABLED = 'TRADING_DISABLED';
const GUARD_DAILY_MAX = 'DAILY_MAX_FILINGS';
const GUARD_PER_TICKER_MAX = 'PER_TICKER_DAILY_MAX';

export const evaluateGuardrails = (
  config: GuardrailConfig,
  context: GuardrailContext,
  logger?: Logger,
): GuardrailDecision => {
  const { tradingEnabled, dailyMaxFilings, perTickerDailyMax } = config;
  const { tradesSubmittedToday, tradesSubmittedTodayForTicker, ticker } = context;

  if (!tradingEnabled) {
    const result: GuardrailDecision = {
      allowed: false,
      guard: GUARD_TRADING_DISABLED,
      message: 'Trading is currently disabled via TRADING_ENABLED',
    };
    logGuardrail(logger, result, context);
    return result;
  }

  if (typeof dailyMaxFilings === 'number' && tradesSubmittedToday >= dailyMaxFilings) {
    const result: GuardrailDecision = {
      allowed: false,
      guard: GUARD_DAILY_MAX,
      message: `Daily max filings reached (${dailyMaxFilings})`,
      context: { tradesSubmittedToday, dailyMaxFilings },
    };
    logGuardrail(logger, result, context);
    return result;
  }

  if (typeof perTickerDailyMax === 'number' && tradesSubmittedTodayForTicker >= perTickerDailyMax) {
    const result: GuardrailDecision = {
      allowed: false,
      guard: GUARD_PER_TICKER_MAX,
      message: `Per-ticker daily max reached for ${ticker}`,
      context: { tradesSubmittedTodayForTicker, perTickerDailyMax, ticker },
    };
    logGuardrail(logger, result, context);
    return result;
  }

  return { allowed: true };
};

export const assertGuardrails = (
  config: GuardrailConfig,
  context: GuardrailContext,
  logger?: Logger,
): void => {
  const decision = evaluateGuardrails(config, context, logger);

  if (!decision.allowed) {
    throw new TradeGuardrailError(decision.message, {
      guard: decision.guard,
      context: { ...context, ...(decision.context ?? {}) },
    });
  }
};

const logGuardrail = (logger: Logger | undefined, decision: GuardrailDecision, context: GuardrailContext) => {
  if (!logger || decision.allowed) {
    return;
  }

  logger.warn(
    {
      guard: decision.guard,
      message: decision.message,
      ticker: context.ticker,
      tradesSubmittedToday: context.tradesSubmittedToday,
      tradesSubmittedTodayForTicker: context.tradesSubmittedTodayForTicker,
      tradingDateWindowStart: context.tradingDateWindowStart.toISOString(),
      tradingDateWindowEnd: context.tradingDateWindowEnd.toISOString(),
      extraContext: decision.context,
    },
    'Trade blocked by guardrail',
  );
};

export const GUARD_NAMES = {
  tradingDisabled: GUARD_TRADING_DISABLED,
  dailyMax: GUARD_DAILY_MAX,
  perTickerMax: GUARD_PER_TICKER_MAX,
} as const;
