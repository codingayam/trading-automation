import { describe, expect, beforeEach, afterEach, it, vi } from 'vitest';
import { PrismockClient } from 'prismock';
import { Prisma, PrismaClient, TradeStatus } from '@prisma/client';

import { createTradeRepository, TradeRepository } from '../trade-repository';
import { UniqueConstraintViolationError } from '../../../errors';

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

describe('TradeRepository', () => {
  let prisma: PrismaClient;
  let repository: TradeRepository;

  beforeEach(() => {
    prisma = createPrismock();
    repository = createTradeRepository(prisma);
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await prisma.$disconnect();
  });

  const baseCreateParams = {
    sourceHash: 'hash-1',
    symbol: 'NVDA',
    notionalSubmitted: '1000',
  } as const;

  it('creates a trade with sensible defaults', async () => {
    const trade = await repository.createTradeAttempt(baseCreateParams);

    expect(trade).toMatchObject({
      sourceHash: baseCreateParams.sourceHash,
      symbol: baseCreateParams.symbol,
      side: 'BUY',
      orderType: 'MARKET',
      timeInForce: 'DAY',
      status: 'NEW',
    });

    expect(trade.notionalSubmitted?.toNumber()).toBe(1000);

    const stored = await prisma.trade.findUnique({ where: { id: trade.id } });
    expect(stored).not.toBeNull();
  });

  it('lists open trades filtered by status', async () => {
    await repository.createTradeAttempt({
      ...baseCreateParams,
      sourceHash: 'hash-open-1',
      status: 'ACCEPTED',
      clientOrderId: 'order-1',
    });

    await repository.createTradeAttempt({
      ...baseCreateParams,
      sourceHash: 'hash-open-2',
      status: 'PARTIALLY_FILLED',
      clientOrderId: 'order-2',
    });

    await repository.createTradeAttempt({
      ...baseCreateParams,
      sourceHash: 'hash-closed',
      status: 'FILLED',
      clientOrderId: 'order-3',
    });

    const open = await repository.listOpenTrades();

    expect(open).toHaveLength(2);
    const openStatuses: TradeStatus[] = ['NEW', 'ACCEPTED', 'PARTIALLY_FILLED'];
    open.forEach((trade) => expect(openStatuses).toContain(trade.status));
  });

  it('maps P2002 unique constraint errors to UniqueConstraintViolationError', async () => {
    const uniqueError = new Prisma.PrismaClientKnownRequestError('Unique constraint failed', {
      code: 'P2002',
      clientVersion: '6.16.2',
      meta: { target: ['trade_source_hash_key'] },
    });

    vi.spyOn(prisma.trade, 'create').mockRejectedValue(uniqueError);

    await expect(repository.createTradeAttempt(baseCreateParams)).rejects.toBeInstanceOf(
      UniqueConstraintViolationError,
    );
  });
});
