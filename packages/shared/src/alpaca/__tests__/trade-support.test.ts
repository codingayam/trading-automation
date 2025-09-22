import { describe, it, beforeEach, afterEach, expect, vi } from 'vitest';
import { Prisma, PrismaClient } from '@prisma/client';
import { PrismockClient } from 'prismock';

import { createTradeRepository } from '../../db/repositories/trade-repository';
import { submitTradeForFiling } from '../trade-support';
import type { AlpacaClient } from '../client';
import type { GuardrailConfig } from '../types';
import { AlpacaInsufficientBuyingPowerError, AlpacaOrderValidationError } from '../../errors';

if (!(globalThis as Record<string, unknown>).Decimal) {
  (globalThis as Record<string, unknown>).Decimal = Prisma.Decimal;
}

const originalStructuredClone = globalThis.structuredClone?.bind(globalThis);

const safeClone = (value: unknown): unknown => {
  if (value instanceof Prisma.Decimal) {
    return new Prisma.Decimal(value.toString());
  }

  if (value instanceof Date) {
    return new Date(value.getTime());
  }

  if (Array.isArray(value)) {
    return value.map((item) => safeClone(item));
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, safeClone(item)]);
    return Object.fromEntries(entries);
  }

  return value;
};

(globalThis as Record<string, unknown>).structuredClone = ((input: unknown) => {
  if (originalStructuredClone) {
    try {
      return originalStructuredClone(input);
    } catch {
      return safeClone(input);
    }
  }

  return safeClone(input);
}) as typeof structuredClone;

const createPrismock = () => new PrismockClient() as unknown as PrismaClient;

const baseGuardrailConfig: GuardrailConfig = {
  tradingEnabled: true,
  paperTrading: true,
  tradeNotionalUsd: 1000,
};

const windowStart = new Date('2024-01-01T14:30:00.000Z');
const windowEnd = new Date('2024-01-02T14:30:00.000Z');

const createMockClient = (): AlpacaClient => {
  const mock: Partial<AlpacaClient> = {
    submitOrder: vi.fn(),
    getOrder: vi.fn(),
    getOrderByClientOrderId: vi.fn(),
    getLatestTrade: vi.fn(),
    getAccount: vi.fn(),
    getPositions: vi.fn(),
  };

  return mock as AlpacaClient;
};

describe('submitTradeForFiling', () => {
  let prisma: PrismaClient;

  beforeEach(() => {
    prisma = createPrismock();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await prisma.$disconnect();
  });

  it('submits a notional order and reconciles to filled status', async () => {
    const repository = createTradeRepository(prisma);
    const alpacaClient = createMockClient();

    const orderId = 'order-123';
    const clientOrderId = 'client-abc';
    const acceptedOrder = {
      id: orderId,
      client_order_id: clientOrderId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      submitted_at: new Date().toISOString(),
      filled_at: null,
      expired_at: null,
      canceled_at: null,
      failed_at: null,
      replaced_at: null,
      replaced_by: null,
      replaces: null,
      asset_id: 'asset-1',
      symbol: 'AAPL',
      asset_class: 'us_equity',
      notional: '1000',
      qty: null,
      filled_qty: '0',
      filled_avg_price: null,
      order_class: '',
      order_type: 'market',
      type: 'market',
      side: 'buy',
      time_in_force: 'day',
      limit_price: null,
      stop_price: null,
      status: 'accepted' as const,
      extended_hours: false,
      legs: null,
      trail_percent: null,
      trail_price: null,
      hwm: null,
      subtag: null,
      source: null,
      position_intent: null,
      expires_at: null,
    };

    const filledOrder = {
      ...acceptedOrder,
      status: 'filled' as const,
      filled_qty: '4',
      filled_avg_price: '250',
      filled_at: new Date().toISOString(),
    };

    (alpacaClient.submitOrder as ReturnType<typeof vi.fn>).mockResolvedValue(acceptedOrder);

    const pollResponses = [acceptedOrder, filledOrder];
    let getOrderCalls = 0;
    (alpacaClient.getOrder as ReturnType<typeof vi.fn>).mockImplementation(async () => {
      const response = pollResponses[Math.min(getOrderCalls, pollResponses.length - 1)];
      getOrderCalls += 1;
      return response;
    });

    const result = await submitTradeForFiling({
      alpacaClient,
      tradeRepository: repository,
      prismaClient: prisma,
      guardrailConfig: baseGuardrailConfig,
      sourceHash: 'hash-1',
      symbol: 'AAPL',
      congressTradeFeedId: 'feed-1',
      clientOrderId,
      tradingDateWindowStart: windowStart,
      tradingDateWindowEnd: windowEnd,
    });

    expect(result.status).toBe('FILLED');
    expect(result.fallbackUsed).toBe(false);
    expect(alpacaClient.submitOrder).toHaveBeenCalledTimes(1);
    expect(alpacaClient.getOrder).toHaveBeenCalled();

    const stored = await prisma.trade.findFirst({ where: { sourceHash: 'hash-1' } });
    expect(stored?.status).toBe('FILLED');
    expect(stored?.notionalSubmitted?.toNumber()).toBe(1000);
  });

  it('falls back to whole-share order when notional submission is rejected', async () => {
    const repository = createTradeRepository(prisma);
    const alpacaClient = createMockClient();

    const clientOrderId = 'client-fallback';
    const baseOrder = {
      id: 'order-fallback',
      client_order_id: clientOrderId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      submitted_at: new Date().toISOString(),
      filled_at: new Date().toISOString(),
      expired_at: null,
      canceled_at: null,
      failed_at: null,
      replaced_at: null,
      replaced_by: null,
      replaces: null,
      asset_id: 'asset-1',
      symbol: 'AAPL',
      asset_class: 'us_equity',
      notional: null,
      qty: '3',
      filled_qty: '3',
      filled_avg_price: '333.33',
      order_class: '',
      order_type: 'market',
      type: 'market',
      side: 'buy',
      time_in_force: 'day',
      limit_price: null,
      stop_price: null,
      status: 'filled' as const,
      extended_hours: false,
      legs: null,
      trail_percent: null,
      trail_price: null,
      hwm: null,
      subtag: null,
      source: null,
      position_intent: null,
      expires_at: null,
    };

    const validationError = new AlpacaOrderValidationError('fractional not supported', { status: 422 });

    const submitOrderMock = alpacaClient.submitOrder as ReturnType<typeof vi.fn>;
    submitOrderMock.mockImplementation(async (payload) => {
      if (payload.notional) {
        throw validationError;
      }
      return baseOrder;
    });

    (alpacaClient.getLatestTrade as ReturnType<typeof vi.fn>).mockResolvedValue({
      symbol: 'AAPL',
      trade: {
        t: new Date().toISOString(),
        price: 310,
        size: 1,
        exchange: 'TEST',
      },
    });

    (alpacaClient.getOrder as ReturnType<typeof vi.fn>).mockResolvedValue(baseOrder);

    const result = await submitTradeForFiling({
      alpacaClient,
      tradeRepository: repository,
      prismaClient: prisma,
      guardrailConfig: baseGuardrailConfig,
      sourceHash: 'hash-2',
      symbol: 'AAPL',
      clientOrderId,
      tradingDateWindowStart: windowStart,
      tradingDateWindowEnd: windowEnd,
    });

    expect(result.fallbackUsed).toBe(true);
    expect(result.qtySubmitted).toBe('3');
    expect(submitOrderMock).toHaveBeenCalledTimes(2);

    const stored = await prisma.trade.findFirst({ where: { sourceHash: 'hash-2' } });
    expect(stored?.qtySubmitted?.toNumber()).toBe(3);
    expect(stored?.notionalSubmitted).toBeNull();
  });

  it('short-circuits when trading is disabled by guardrail', async () => {
    const repository = createTradeRepository(prisma);
    const alpacaClient = createMockClient();
    const config: GuardrailConfig = { ...baseGuardrailConfig, tradingEnabled: false };

    const result = await submitTradeForFiling({
      alpacaClient,
      tradeRepository: repository,
      prismaClient: prisma,
      guardrailConfig: config,
      sourceHash: 'hash-3',
      symbol: 'MSFT',
      tradingDateWindowStart: windowStart,
      tradingDateWindowEnd: windowEnd,
    });

    expect(result.guardrailBlocked).toBe(true);
    expect(result.status).toBe('failed');
    expect(alpacaClient.submitOrder).not.toHaveBeenCalled();

    const stored = await prisma.trade.findFirst({ where: { sourceHash: 'hash-3' } });
    expect(stored?.status).toBe('FAILED');
  });

  it('marks trade as failed and rethrows when buying power is insufficient', async () => {
    const repository = createTradeRepository(prisma);
    const alpacaClient = createMockClient();

    const error = new AlpacaInsufficientBuyingPowerError('insufficient buying power', { status: 403 });
    (alpacaClient.submitOrder as ReturnType<typeof vi.fn>).mockRejectedValue(error);

    await expect(
      submitTradeForFiling({
        alpacaClient,
        tradeRepository: repository,
        prismaClient: prisma,
        guardrailConfig: baseGuardrailConfig,
        sourceHash: 'hash-4',
        symbol: 'TSLA',
        tradingDateWindowStart: windowStart,
        tradingDateWindowEnd: windowEnd,
      }),
    ).rejects.toBe(error);

    const stored = await prisma.trade.findFirst({ where: { sourceHash: 'hash-4' } });
    expect(stored?.status).toBe('FAILED');
    expect(stored?.failedAt).not.toBeNull();
  });
});
