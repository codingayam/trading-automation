import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { Prisma, type PrismaClient } from '@prisma/client';
import { PrismockClient } from 'prismock';
import { createTradeRepository } from '@trading-automation/shared';
import * as rateLimit from '../../../lib/rate-limit';
import { setTradeRepositoryForTesting, resetTradeRepositoryForTesting } from '../../../lib/trade-service';
import { GET } from './route';

process.env.DATABASE_URL ??= 'postgresql://postgres:postgres@localhost:5432/trading-test';
process.env.ALPACA_BASE_URL ??= 'https://paper-api.alpaca.markets';
process.env.ALPACA_DATA_BASE_URL ??= 'https://data.alpaca.markets';

const decimal = (value: number) => new Prisma.Decimal(value);

let rateLimitSpy: ReturnType<typeof vi.spyOn<typeof rateLimit, 'applyRateLimit'>>;
let prismock: PrismaClient;

describe('GET /api/trades', () => {
  beforeEach(async () => {
    prismock = new PrismockClient() as unknown as PrismaClient;
    const repository = createTradeRepository(prismock);
    setTradeRepositoryForTesting(repository);

    await prismock.trade.create({
      data: {
        id: 'trade-1',
        sourceHash: 'hash-1',
        symbol: 'NVDA',
        status: 'FILLED',
        side: 'BUY',
        orderType: 'MARKET',
        timeInForce: 'DAY',
        notionalSubmitted: decimal(1000),
        qtySubmitted: decimal(5),
        filledQty: decimal(5),
        filledAvgPrice: decimal(200),
        clientOrderId: 'client-1',
        alpacaOrderId: 'alpaca-1',
        createdAt: new Date('2024-02-16T14:30:00Z'),
        submittedAt: new Date('2024-02-16T14:30:30Z'),
        updatedAt: new Date('2024-02-16T14:31:00Z'),
        filledAt: new Date('2024-02-16T14:31:00Z'),
        canceledAt: null,
        failedAt: null,
        rawOrderJson: Prisma.JsonNull,
        congressTradeFeedId: null,
      },
    });

    await prismock.trade.create({
      data: {
        id: 'trade-2',
        sourceHash: 'hash-2',
        symbol: 'AAPL',
        status: 'ACCEPTED',
        side: 'BUY',
        orderType: 'MARKET',
        timeInForce: 'DAY',
        notionalSubmitted: decimal(1000),
        qtySubmitted: decimal(5.12),
        filledQty: decimal(0),
        filledAvgPrice: null,
        clientOrderId: 'client-2',
        alpacaOrderId: 'alpaca-2',
        createdAt: new Date('2024-02-15T13:00:00Z'),
        submittedAt: new Date('2024-02-15T13:00:30Z'),
        updatedAt: new Date('2024-02-15T13:01:00Z'),
        filledAt: null,
        canceledAt: null,
        failedAt: null,
        rawOrderJson: Prisma.JsonNull,
        congressTradeFeedId: null,
      },
    });

    rateLimitSpy = vi.spyOn(rateLimit, 'applyRateLimit').mockReturnValue({ allowed: true, remaining: 29, limit: 30 });
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    resetTradeRepositoryForTesting();
    await prismock?.$disconnect?.();
  });

  it('returns serialized trades with pagination and summary', async () => {
    const request = new NextRequest(new URL('http://localhost/api/trades?page=1&pageSize=25'));
    const response = await GET(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.trades).toHaveLength(2);
    expect(body.pagination.total).toBe(2);
    expect(body.summary.statusCounts.FILLED).toBe(1);
    expect(body.summary.statusCounts.ACCEPTED).toBe(1);
    expect(body.summary.totalNotional).toBe(2000);
  });

  it('returns 400 for invalid date filters', async () => {
    const request = new NextRequest(new URL('http://localhost/api/trades?startDate=2024-03-10&endDate=2024-03-01'));

    const response = await GET(request);
    expect(response.status).toBe(400);

    const body = await response.json();
    expect(body.error).toContain('startDate');
  });

  it('returns 429 when rate limiter denies the request', async () => {
    rateLimitSpy.mockReturnValueOnce({
      allowed: false,
      remaining: 0,
      limit: 1,
      retryAfterMs: 1000,
    });

    const request = new NextRequest(new URL('http://localhost/api/trades'));
    const response = await GET(request);

    expect(response.status).toBe(429);
    const body = await response.json();
    expect(body.error).toContain('Rate limit');
  });
});
