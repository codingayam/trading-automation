import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { Prisma, PrismaClient } from '@prisma/client';
import { PrismockClient } from 'prismock';
import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest';
import type { SpyInstance } from 'vitest';

import {
  AlpacaClient,
  AlpacaOrderValidationError,
  QuiverClient,
  createLogger,
  formatDateKey,
  loadWorkerEnv,
  type WorkerEnv,
} from '@trading-automation/shared';
import * as shared from '@trading-automation/shared';

import { runOpenJob } from '../open-job-runner.js';

const FIXTURE_ROOT = resolve(__dirname, '../../../../packages/shared/fixtures');

const readFixture = <T>(relativePath: string): T => {
  const contents = readFileSync(resolve(FIXTURE_ROOT, relativePath), 'utf8');
  return JSON.parse(contents) as T;
};

// Prismock relies on Decimal / structuredClone being present just like shared unit tests.
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

const quiverFixtures: Record<string, unknown[]> = {
  '2024-02-15': readFixture('quiver/congresstrading-2024-02-15.json'),
  '2024-02-16': readFixture('quiver/congresstrading-2024-02-16.json'),
};

const alpacaOrderAcceptedFixture = readFixture<Record<string, unknown>>('alpaca/order-notional-accepted.json');
const alpacaOrderFilledFixture = readFixture<Record<string, unknown>>('alpaca/order-filled.json');
const alpacaValidationFixture = readFixture<{ code: number; message: string; data?: Array<{ message: string }> }>(
  'alpaca/order-validation-422.json',
);
const alpacaClockFixture = readFixture<{ timestamp: string; is_open: boolean; next_open: string; next_close: string }>(
  'alpaca/clock-open.json',
);
const alpacaCalendarFixture = readFixture<Array<{ date: string; open: string; close: string; session_open?: string; session_close?: string }>>(
  'alpaca/calendar-2024-02-16.json',
);
const alpacaLatestTradeFixture = readFixture<{ symbol: string; trade: { t: string; price: number; size: number; exchange: string; conditions?: string[] } }>(
  'alpaca/latest-trade-aapl.json',
);

const deepClone = <T>(value: T): T => JSON.parse(JSON.stringify(value));

describe('runOpenJob integration (fixtures)', () => {
  let prisma: PrismaClient;
  let env: Readonly<WorkerEnv>;
  let quiverSpy: SpyInstance;
  let clockSpy: SpyInstance;
  let calendarSpy: SpyInstance;

  beforeEach(() => {
    prisma = new PrismockClient() as unknown as PrismaClient;
    vi.spyOn(shared, 'getPrismaClient').mockReturnValue(prisma);

    env = loadWorkerEnv({
      NODE_ENV: 'test',
      LOG_LEVEL: 'fatal',
      SERVICE_NAME: 'open-job-worker-test',
      DATABASE_URL: 'postgresql://test:test@localhost:5432/test',
      ALPACA_KEY_ID: 'alpaca-key',
      ALPACA_SECRET_KEY: 'alpaca-secret',
      QUIVER_API_KEY: 'quiver-key',
    });

    const calendarResponse = [
      {
        date: '2024-02-15',
        open: '09:30',
        close: '16:00',
        session_open: '04:00',
        session_close: '20:00',
      },
      ...alpacaCalendarFixture,
    ];

    clockSpy = vi.spyOn(AlpacaClient.prototype, 'getClock');
    clockSpy.mockResolvedValue(deepClone(alpacaClockFixture));
    calendarSpy = vi.spyOn(AlpacaClient.prototype, 'getCalendar');
    calendarSpy.mockImplementation(async () => deepClone(calendarResponse));

    const orderQueues = new Map<string, Array<Record<string, unknown>>>();

    vi.spyOn(AlpacaClient.prototype, 'submitOrder').mockImplementation(async (payload) => {
      const symbol = payload.symbol;
      const clientOrderId = payload.client_order_id ?? `auto-${symbol}`;

      if (payload.notional && symbol === 'BRK.B') {
        throw new AlpacaOrderValidationError(alpacaValidationFixture.message, {
          status: 422,
          errorCode: alpacaValidationFixture.code,
          body: alpacaValidationFixture,
          violations: alpacaValidationFixture.data?.map((item) => item.message),
        });
      }

      if (payload.notional) {
        const acceptedOrder = {
          ...deepClone(alpacaOrderAcceptedFixture),
          id: `order-${symbol}-notional`,
          client_order_id: clientOrderId,
          symbol,
          notional: payload.notional,
          qty: null,
        };

        const filledOrder = {
          ...deepClone(alpacaOrderFilledFixture),
          id: acceptedOrder.id,
          client_order_id: clientOrderId,
          symbol,
          notional: payload.notional,
          qty: '5',
        };

        orderQueues.set(acceptedOrder.id, [acceptedOrder, filledOrder]);
        return acceptedOrder as typeof alpacaOrderAcceptedFixture;
      }

      const qtyString = payload.qty ?? '0';
      const fallbackOrder = {
        ...deepClone(alpacaOrderFilledFixture),
        id: `order-${symbol}-fallback`,
        client_order_id: clientOrderId,
        symbol,
        notional: null,
        qty: qtyString,
        filled_qty: qtyString,
        status: 'filled',
      };

      orderQueues.set(fallbackOrder.id, [fallbackOrder]);
      return fallbackOrder as typeof alpacaOrderFilledFixture;
    });

    vi.spyOn(AlpacaClient.prototype, 'getOrder').mockImplementation(async ({ orderId }) => {
      const queue = orderQueues.get(orderId);
      if (!queue || queue.length === 0) {
        throw new Error(`Order ${orderId} not found in mock queue`);
      }

      const [next, ...rest] = queue;
      orderQueues.set(orderId, rest);
      return deepClone(next) as typeof alpacaOrderFilledFixture;
    });

    vi.spyOn(AlpacaClient.prototype, 'getLatestTrade').mockImplementation(async ({ symbol }) => {
      const cloned = deepClone(alpacaLatestTradeFixture);
      cloned.symbol = symbol;
      return cloned as typeof alpacaLatestTradeFixture;
    });

    quiverSpy = vi.spyOn(QuiverClient.prototype, 'getCongressTradingByDate');
    quiverSpy.mockImplementation(async ({ date }) => {
      const resolvedDate = date instanceof Date ? formatDateKey(date) : date;
      const fixture = quiverFixtures[resolvedDate];
      return fixture ? (deepClone(fixture) as Record<string, unknown>[]) : [];
    });
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await prisma.$disconnect();
  });

  it('does not resubmit trades when re-run on the same trading date', async () => {
    const logger = createLogger({ level: 'fatal' });
    const now = () => new Date('2024-02-16T14:30:00.000Z');

    const firstRun = await runOpenJob({ env, logger, now });
    expect(firstRun.status).toBe('success');

    const tradesAfterFirstRun = await prisma.trade.findMany();
    expect(tradesAfterFirstRun).toHaveLength(3);

    quiverSpy.mockClear();

    const secondRun = await runOpenJob({ env, logger, now });

    expect(secondRun.status).toBe('success');
    expect(secondRun.summary.trades.attempted).toBe(0);
    expect(secondRun.summary.trades.submitted).toBe(0);
    expect(secondRun.summary.errors).toEqual([]);
    const [previousWindow, currentWindow] = secondRun.summary.windows;
    expect(previousWindow?.filingsFetched).toBe(0);
    expect(currentWindow?.filingsConsidered).toBe(0);
    expect(quiverSpy).toHaveBeenCalled();

    const tradesAfterSecondRun = await prisma.trade.findMany();
    expect(tradesAfterSecondRun).toHaveLength(tradesAfterFirstRun.length);

    const jobRuns = await prisma.jobRun.findMany({ orderBy: { createdAt: 'asc' } });
    expect(jobRuns).toHaveLength(2);
    expect(jobRuns[0]?.status).toBe('SUCCESS');
    expect(jobRuns[1]?.status).toBe('SUCCESS');
  });

  it('marks filings that fall outside the trading window', async () => {
    const logger = createLogger({ level: 'fatal' });
    const now = () => new Date('2024-02-16T14:30:00.000Z');
    const lateRecord: Record<string, unknown> = {
      Ticker: 'AAPL',
      Name: 'Rep. Late Filing',
      Transaction: 'Purchase',
      Filed: '2024-02-17',
      Traded: '2024-02-17',
      Party: 'D',
    };

    quiverSpy.mockImplementation(async ({ date }) => {
      const resolvedDate = date instanceof Date ? formatDateKey(date) : date;
      if (resolvedDate === '2024-02-15') {
        return [lateRecord];
      }
      return [];
    });

    const result = await runOpenJob({ env, logger, now });

    expect(result.status).toBe('success');
    expect(result.summary.errors).toEqual([]);
    const [previousWindow, currentWindow] = result.summary.windows;
    expect(previousWindow?.filingsFetched).toBe(1);
    expect(previousWindow?.filingsConsidered).toBe(0);
    expect(previousWindow?.outsideWindow).toBe(1);
    expect(currentWindow?.filingsFetched).toBe(0);
    expect(result.summary.trades.submitted).toBe(0);

    const checkpoints = await prisma.ingestCheckpoint.findMany({ orderBy: { tradingDateEt: 'asc' } });
    expect(checkpoints).toHaveLength(2);
  });

  it('fetches filings that fall on non-trading days between sessions', async () => {
    const logger = createLogger({ level: 'fatal' });
    const now = () => new Date('2024-02-19T14:29:55.000Z');

    const saturdayRecord: Record<string, unknown> = {
      Ticker: 'TSLA',
      Name: 'Rep. Saturday Filing',
      Transaction: 'Purchase',
      Filed: '2024-02-17',
      Traded: '2024-02-16',
      Party: 'R',
    };

    const sundayRecord: Record<string, unknown> = {
      Ticker: 'MSFT',
      Name: 'Rep. Sunday Filing',
      Transaction: 'Purchase',
      Filed: '2024-02-18',
      Traded: '2024-02-18',
      Party: 'D',
    };

    const originalSaturday = quiverFixtures['2024-02-17'];
    const originalSunday = quiverFixtures['2024-02-18'];

    quiverFixtures['2024-02-17'] = [saturdayRecord];
    quiverFixtures['2024-02-18'] = [sundayRecord];

    clockSpy.mockResolvedValueOnce({
      timestamp: '2024-02-19T14:29:55.000Z',
      is_open: true,
      next_open: '2024-02-20T14:30:00.000Z',
      next_close: '2024-02-19T21:00:00.000Z',
    });

    calendarSpy.mockResolvedValueOnce([
      {
        date: '2024-02-16',
        open: '09:30',
        close: '16:00',
        session_open: '04:00',
        session_close: '20:00',
      },
      {
        date: '2024-02-19',
        open: '09:30',
        close: '16:00',
        session_open: '04:00',
        session_close: '20:00',
      },
    ]);

    try {
      const result = await runOpenJob({ env, logger, now, dryRun: true });

      expect(result.status).toBe('success');

      const requestedDates = quiverSpy.mock.calls.map(([params]) =>
        formatDateKey(params.date instanceof Date ? params.date : new Date(params.date as string)),
      );

      expect(requestedDates).toEqual(expect.arrayContaining(['2024-02-17', '2024-02-18', '2024-02-19']));

      const currentWindowSummary = result.summary.windows.find((window) => window.label === 'current');
      expect(currentWindowSummary?.filingsFetched).toBeGreaterThanOrEqual(2);
      expect(currentWindowSummary?.filingsConsidered).toBe(2);
      expect(result.summary.trades.dryRunSkipped).toBeGreaterThanOrEqual(2);
    } finally {
      if (originalSaturday) {
        quiverFixtures['2024-02-17'] = originalSaturday;
      } else {
        delete quiverFixtures['2024-02-17'];
      }

      if (originalSunday) {
        quiverFixtures['2024-02-18'] = originalSunday;
      } else {
        delete quiverFixtures['2024-02-18'];
      }
    }
  });

  it('processes Quiver filings and records trades using Alpaca fixtures', async () => {
    const logger = createLogger({ level: 'fatal' });
    const now = () => new Date('2024-02-16T14:30:00.000Z');

    const result = await runOpenJob({ env, logger, now });

    expect(result.status).toBe('success');
    expect(result.summary.trades.submitted).toBe(3);
    expect(result.summary.trades.fallbackUsed).toBe(1);
    expect(result.summary.trades.guardrailBlocked).toBe(0);
    expect(result.summary.errors).toEqual([]);

    const jobRuns = await prisma.jobRun.findMany();
    expect(jobRuns).toHaveLength(1);
    expect(jobRuns[0]?.status).toBe('SUCCESS');

    const checkpoints = await prisma.ingestCheckpoint.findMany({ orderBy: { tradingDateEt: 'asc' } });
    expect(checkpoints).toHaveLength(2);

    const trades = await prisma.trade.findMany({ orderBy: { symbol: 'asc' } });
    expect(trades).toHaveLength(3);

    const fallbackTrade = trades.find((trade) => trade.symbol === 'BRK.B');
    expect(fallbackTrade?.notionalSubmitted).toBeNull();
    expect(fallbackTrade?.qtySubmitted?.toNumber()).toBeGreaterThan(0);

    const feedEntries = await prisma.congressTradeFeed.findMany();
    expect(feedEntries).toHaveLength(3);
  });
});
