import type { TradeStatus } from '@prisma/client';

import type { Logger } from '../logger.js';
import type { TradeRepository } from '../db/repositories/trade-repository.js';
import type { AlpacaClient } from './client.js';
import type { AlpacaOrder } from './types.js';
import { buildTradeUpdateFromOrder, isTerminalTradeStatus } from './status.js';

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export interface PollOrderStatusOptions {
  alpacaClient: AlpacaClient;
  tradeRepository: TradeRepository;
  tradeId: string;
  alpacaOrderId?: string;
  clientOrderId?: string;
  timeoutMs?: number;
  initialDelayMs?: number;
  backoffFactor?: number;
  maxDelayMs?: number;
  logger?: Logger;
}

export interface PollOrderStatusResult {
  order: AlpacaOrder;
  tradeStatus: TradeStatus;
  attempts: number;
  durationMs: number;
  timedOut: boolean;
}

const DEFAULT_INITIAL_DELAY_MS = 1_000;
const DEFAULT_BACKOFF_FACTOR = 1.6;
const DEFAULT_MAX_DELAY_MS = 5_000;
const DEFAULT_TIMEOUT_MS = 60_000;

const resolveOrder = async (
  client: AlpacaClient,
  params: { alpacaOrderId?: string; clientOrderId?: string },
): Promise<AlpacaOrder> => {
  if (params.alpacaOrderId) {
    return client.getOrder({ orderId: params.alpacaOrderId });
  }

  if (!params.clientOrderId) {
    throw new Error('pollOrderStatus requires alpacaOrderId or clientOrderId');
  }

  return client.getOrderByClientOrderId({ clientOrderId: params.clientOrderId });
};

export const pollOrderStatus = async (options: PollOrderStatusOptions): Promise<PollOrderStatusResult> => {
  const {
    alpacaClient,
    tradeRepository,
    tradeId,
    alpacaOrderId,
    clientOrderId,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    initialDelayMs = DEFAULT_INITIAL_DELAY_MS,
    backoffFactor = DEFAULT_BACKOFF_FACTOR,
    maxDelayMs = DEFAULT_MAX_DELAY_MS,
    logger,
  } = options;

  const startedAt = Date.now();
  let attempts = 0;
  let delayMs = initialDelayMs;
  let lastOrder: AlpacaOrder | undefined;
  let lastStatus: TradeStatus | undefined;

  while (Date.now() - startedAt <= timeoutMs) {
    attempts += 1;

    const order = await resolveOrder(alpacaClient, { alpacaOrderId, clientOrderId });
    lastOrder = order;
    const tradeUpdate = buildTradeUpdateFromOrder(order);
    lastStatus = tradeUpdate.status;

    await tradeRepository.updateTrade({
      id: tradeId,
      ...tradeUpdate,
    });

    if (isTerminalTradeStatus(tradeUpdate.status)) {
      const durationMs = Date.now() - startedAt;
      logger?.info(
        {
          tradeId,
          alpacaOrderId: order.id,
          clientOrderId: order.client_order_id,
          status: tradeUpdate.status,
          attempts,
          durationMs,
        },
        'Order polling completed with terminal status',
      );

      return {
        order,
        tradeStatus: tradeUpdate.status,
        attempts,
        durationMs,
        timedOut: false,
      };
    }

    logger?.debug(
      {
        tradeId,
        alpacaOrderId: order.id,
        clientOrderId: order.client_order_id,
        status: tradeUpdate.status,
        attempts,
        delayMs,
      },
      'Order still in-flight; scheduling next poll',
    );

    await sleep(delayMs);
    delayMs = Math.min(Math.round(delayMs * backoffFactor), maxDelayMs);
  }

  if (!lastOrder || !lastStatus) {
    throw new Error('pollOrderStatus did not receive an order response during polling');
  }

  const durationMs = Date.now() - startedAt;
  logger?.warn(
    {
      tradeId,
      alpacaOrderId: lastOrder.id,
      clientOrderId: lastOrder.client_order_id,
      status: lastStatus,
      attempts,
      durationMs,
    },
    'Order polling reached timeout without terminal status',
  );

  return {
    order: lastOrder,
    tradeStatus: lastStatus,
    attempts,
    durationMs,
    timedOut: true,
  };
};
