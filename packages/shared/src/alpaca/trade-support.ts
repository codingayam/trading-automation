import type { PrismaClient, Trade } from '@prisma/client';

import type { Logger } from '../logger';
import { createLogger } from '../logger';
import type { TradeRepository } from '../db/repositories/trade-repository';
import { runInTransaction, type TransactionClient } from '../db/transactions';
import {
  AlpacaError,
  AlpacaInsufficientBuyingPowerError,
  AlpacaOrderValidationError,
  TradeGuardrailError,
} from '../errors';
import type { AlpacaClient } from './client';
import { pollOrderStatus } from './polling';
import { buildTradeUpdateFromOrder } from './status';
import { assertGuardrails } from './guardrails';
import type { GuardrailConfig, GuardrailContext, SubmitTradeResult } from './types';
import type { AlpacaOrder } from './types';

const DEFAULT_LOGGER = createLogger({ name: 'alpaca-trade-support' });

export interface SubmitTradeForFilingParams {
  alpacaClient: AlpacaClient;
  tradeRepository: TradeRepository;
  prismaClient: PrismaClient;
  guardrailConfig: GuardrailConfig;
  sourceHash: string;
  symbol: string;
  congressTradeFeedId?: string;
  clientOrderId?: string;
  tradingDateWindowStart: Date;
  tradingDateWindowEnd: Date;
  logger?: Logger;
  now?: () => Date;
}

const toNotionalString = (amount: number): string => amount.toFixed(2);

const deriveClientOrderId = (sourceHash: string, preferred?: string): string => {
  const candidate = preferred ?? sourceHash;
  return candidate.slice(0, 48);
};

const shouldFallbackToWholeShares = (error: AlpacaOrderValidationError): boolean => {
  const sources = [error.message, ...(error.violations ?? [])];
  return sources.some((item) => /notional|fraction/i.test(item));
};

const computeWholeShareQty = (notional: number, lastPrice: number): number => {
  if (lastPrice <= 0) {
    return 0;
  }
  return Math.floor(notional / lastPrice);
};

const gatherGuardrailContext = async (
  repository: TradeRepository,
  windowStart: Date,
  windowEnd: Date,
  symbol: string,
  tx?: TransactionClient,
): Promise<Pick<GuardrailContext, 'tradesSubmittedToday' | 'tradesSubmittedTodayForTicker'>> => {
  const tradesSubmittedToday = await repository.countTradesInWindow({ windowStart, windowEnd, tx });
  const tradesSubmittedTodayForTicker = await repository.countTradesInWindow({ windowStart, windowEnd, symbol, tx });

  return { tradesSubmittedToday, tradesSubmittedTodayForTicker };
};

const createTradeRecord = async (
  repository: TradeRepository,
  tx: TransactionClient | undefined,
  params: {
    sourceHash: string;
    symbol: string;
    notional: string;
    congressTradeFeedId?: string;
    clientOrderId: string;
  },
): Promise<Trade> => {
  return repository.createTradeAttempt(
    {
      sourceHash: params.sourceHash,
      symbol: params.symbol,
      notionalSubmitted: params.notional,
      congressTradeFeedId: params.congressTradeFeedId,
      clientOrderId: params.clientOrderId,
      status: 'NEW',
    },
    tx,
  );
};

const markTradeFailure = async (
  repository: TradeRepository,
  tradeId: string,
  now: () => Date,
  details: Record<string, unknown>,
) => {
  await repository.updateTrade({
    id: tradeId,
    status: 'FAILED',
    failedAt: now(),
    rawOrderJson: details,
  });
};

export const submitTradeForFiling = async (
  params: SubmitTradeForFilingParams,
): Promise<SubmitTradeResult> => {
  const {
    alpacaClient,
    tradeRepository,
    prismaClient,
    guardrailConfig,
    sourceHash,
    symbol,
    congressTradeFeedId,
    clientOrderId: preferredClientOrderId,
    tradingDateWindowStart,
    tradingDateWindowEnd,
    logger = DEFAULT_LOGGER,
    now = () => new Date(),
  } = params;

  const notionalString = toNotionalString(guardrailConfig.tradeNotionalUsd);
  const derivedClientOrderId = deriveClientOrderId(sourceHash, preferredClientOrderId);

  let trade: Trade;
  let clientOrderId = derivedClientOrderId;

  try {
    const txnResult = await runInTransaction(prismaClient, async (tx) => {
      const guardrailCounts = await gatherGuardrailContext(
        tradeRepository,
        tradingDateWindowStart,
        tradingDateWindowEnd,
        symbol,
        tx,
      );

      assertGuardrails(
        guardrailConfig,
        {
          tradingDateWindowStart,
          tradingDateWindowEnd,
          ticker: symbol,
          ...guardrailCounts,
        },
        logger,
      );

      const created = await createTradeRecord(tradeRepository, tx, {
        sourceHash,
        symbol,
        notional: notionalString,
        congressTradeFeedId,
        clientOrderId,
      });

      return { trade: created };
    });

    trade = txnResult.trade;
  } catch (error) {
    if (error instanceof TradeGuardrailError) {
      logger.warn(
        {
          guard: error.guard,
          context: error.context,
          sourceHash,
          symbol,
        },
        'Trade blocked due to guardrail prior to order submission',
      );

      const blockedTrade = await tradeRepository.createTradeAttempt({
        sourceHash,
        symbol,
        status: 'FAILED',
        notionalSubmitted: notionalString,
        congressTradeFeedId,
        clientOrderId,
      });

      await markTradeFailure(tradeRepository, blockedTrade.id, now, {
        guard: error.guard,
        guardContext: error.context,
      });

      return {
        tradeId: blockedTrade.id,
        clientOrderId: blockedTrade.clientOrderId ?? clientOrderId,
        status: 'failed',
        guardrailBlocked: true,
      };
    }

    throw error;
  }

  clientOrderId = trade.clientOrderId ?? clientOrderId;

  let order: AlpacaOrder | undefined;
  let fallbackUsed = false;
  let qtySubmitted: string | undefined;

  try {
    order = await submitNotionalOrder(alpacaClient, {
      symbol,
      clientOrderId,
      notional: notionalString,
      logger,
    });
  } catch (error) {
    if (error instanceof AlpacaInsufficientBuyingPowerError) {
      logger.error(
        {
          tradeId: trade.id,
          symbol,
          message: error.message,
        },
        'Alpaca rejected order due to insufficient buying power',
      );
      await markTradeFailure(tradeRepository, trade.id, now, {
        reason: 'INSUFFICIENT_BUYING_POWER',
        message: error.message,
        status: error.status,
      });
      throw error;
    }

    throw error;
  }

  if (!order) {
    fallbackUsed = true;
    try {
      const fallback = await submitFallbackOrder({
        alpacaClient,
        tradeRepository,
        trade,
        symbol,
        clientOrderId,
        notional: guardrailConfig.tradeNotionalUsd,
        now,
        logger,
      });
      order = fallback.order;
      qtySubmitted = fallback.qty;
    } catch (fallbackError) {
      if (fallbackError instanceof TradeGuardrailError) {
        await markTradeFailure(tradeRepository, trade.id, now, {
          guard: fallbackError.guard,
          guardContext: fallbackError.context,
        });
        return {
          tradeId: trade.id,
          clientOrderId,
          status: 'failed',
          guardrailBlocked: true,
          fallbackUsed,
        };
      }

      await markTradeFailure(tradeRepository, trade.id, now, {
        reason: 'FALLBACK_SUBMISSION_FAILED',
        message: fallbackError instanceof Error ? fallbackError.message : 'Unknown error',
      });
      throw fallbackError;
    }
  }

  if (!order) {
    const message = 'Order submission did not produce an Alpaca order response';
    await markTradeFailure(tradeRepository, trade.id, now, { reason: 'NO_ORDER', message });
    throw new AlpacaError(message, { status: 0 });
  }

  const tradeUpdate = buildTradeUpdateFromOrder(order);
  const notionalForRecord = order.notional ?? (fallbackUsed ? null : notionalString);

  await tradeRepository.updateTrade({
    id: trade.id,
    ...tradeUpdate,
    notionalSubmitted: notionalForRecord,
    qtySubmitted: qtySubmitted ?? order.qty ?? undefined,
  });

  const pollResult = await pollOrderStatus({
    alpacaClient,
    tradeRepository,
    tradeId: trade.id,
    alpacaOrderId: order.id,
    clientOrderId: order.client_order_id,
    logger,
  });

  return {
    tradeId: trade.id,
    alpacaOrderId: order.id,
    clientOrderId: order.client_order_id,
    status: pollResult.tradeStatus,
    fallbackUsed,
    guardrailBlocked: false,
    notionalSubmitted: notionalForRecord,
    qtySubmitted,
  };
};

interface SubmitNotionalOrderParams {
  symbol: string;
  clientOrderId: string;
  notional: string;
  logger: Logger;
}

const submitNotionalOrder = async (
  alpacaClient: AlpacaClient,
  params: SubmitNotionalOrderParams,
): Promise<AlpacaOrder | undefined> => {
  const { symbol, clientOrderId, notional, logger } = params;

  try {
    return await alpacaClient.submitOrder({
      symbol,
      side: 'buy',
      type: 'market',
      time_in_force: 'day',
      notional,
      client_order_id: clientOrderId,
    });
  } catch (error) {
    if (error instanceof AlpacaOrderValidationError && shouldFallbackToWholeShares(error)) {
      logger.info(
        {
          symbol,
          clientOrderId,
          violations: error.violations,
        },
        'Alpaca rejected notional order; attempting whole-share fallback',
      );
      return undefined;
    }

    throw error;
  }
};

interface SubmitFallbackOrderParams {
  alpacaClient: AlpacaClient;
  tradeRepository: TradeRepository;
  trade: Trade;
  symbol: string;
  clientOrderId: string;
  notional: number;
  now: () => Date;
  logger: Logger;
}

const submitFallbackOrder = async (
  params: SubmitFallbackOrderParams,
): Promise<{ order: AlpacaOrder; qty: string }> => {
  const { alpacaClient, tradeRepository, trade, symbol, clientOrderId, notional, now, logger } = params;

  const latestTrade = await alpacaClient.getLatestTrade({ symbol });
  const lastPrice = latestTrade.trade?.price;

  if (!lastPrice || lastPrice <= 0) {
    const message = 'Unable to determine latest trade price for fallback order';
    await markTradeFailure(tradeRepository, trade.id, now, {
      reason: 'FALLBACK_PRICE_UNAVAILABLE',
      symbol,
      latestTrade,
    });
    throw new AlpacaError(message, { status: 422 });
  }

  const qty = computeWholeShareQty(notional, lastPrice);

  if (qty <= 0) {
    const message = 'Calculated fallback quantity is zero; skipping order';
    throw new TradeGuardrailError(message, {
      guard: 'FALLBACK_QTY_ZERO',
      context: { symbol, notional, lastPrice },
    });
  }

  const qtyString = qty.toString();

  const order = await alpacaClient.submitOrder({
    symbol,
    side: 'buy',
    type: 'market',
    time_in_force: 'day',
    qty: qtyString,
    client_order_id: clientOrderId,
  });

  await tradeRepository.updateTrade({
    id: trade.id,
    qtySubmitted: qtyString,
    notionalSubmitted: null,
  });

  logger.info(
    {
      tradeId: trade.id,
      symbol,
      qty: qtyString,
      lastPrice,
    },
    'Submitted fallback whole-share order',
  );

  return { order, qty: qtyString };
};
