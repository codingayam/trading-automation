import { NextResponse, type NextRequest } from 'next/server';
import type { Trade } from '@prisma/client';
import { createLogger } from '@trading-automation/shared';
import { applyRateLimit } from '../../../lib/rate-limit';
import { getClientAddress } from '../../../lib/request';
import { listTrades } from '../../../lib/trade-service';
import { parseTradeQuery } from '../../../lib/trade-query';

const logger = createLogger({ name: 'api-trades' });

const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined) {
    return null;
  }

  const numeric = Number(value);
  return Number.isNaN(numeric) ? null : numeric;
};

const serializeTrade = (trade: Trade) => ({
  id: trade.id,
  symbol: trade.symbol,
  status: trade.status,
  createdAt: trade.createdAt.toISOString(),
  updatedAt: trade.updatedAt.toISOString(),
  submittedAt: trade.submittedAt?.toISOString() ?? null,
  filledAt: trade.filledAt?.toISOString() ?? null,
  clientOrderId: trade.clientOrderId ?? null,
  alpacaOrderId: trade.alpacaOrderId ?? null,
  notionalSubmitted: toNumber(trade.notionalSubmitted),
  qtySubmitted: toNumber(trade.qtySubmitted),
  filledQty: toNumber(trade.filledQty),
  filledAvgPrice: toNumber(trade.filledAvgPrice),
});

export async function GET(request: NextRequest) {
  const address = getClientAddress(request);
  const rate = applyRateLimit(`trades:${address}`);

  if (!rate.allowed) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again shortly.' },
      {
        status: 429,
        headers: {
          'Retry-After': rate.retryAfterMs ? Math.ceil(rate.retryAfterMs / 1000).toString() : '60',
        },
      },
    );
  }

  let filters;
  try {
    filters = parseTradeQuery(request.nextUrl.searchParams);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Invalid query parameters' },
      { status: 400 },
    );
  }

  try {
    const { trades, total, page, pageSize } = await listTrades(filters);

    const serialized = trades.map(serializeTrade);

    const statusSummary = serialized.reduce<Record<string, number>>((acc, trade) => {
      acc[trade.status] = (acc[trade.status] ?? 0) + 1;
      return acc;
    }, {});

    const totalNotional = serialized.reduce((sum, trade) => sum + (trade.notionalSubmitted ?? 0), 0);
    const filledNotional = serialized.reduce((sum, trade) => {
      if (trade.status === 'FILLED' || trade.status === 'PARTIALLY_FILLED') {
        return sum + (trade.notionalSubmitted ?? 0);
      }
      return sum;
    }, 0);

    const latestUpdate = serialized.reduce<string | null>((latest, trade) => {
      if (!latest || trade.updatedAt > latest) {
        return trade.updatedAt;
      }
      return latest;
    }, null);

    const totalPages = Math.max(1, Math.ceil(total / pageSize));

    return NextResponse.json({
      trades: serialized,
      pagination: {
        page,
        pageSize,
        total,
        totalPages,
      },
      summary: {
        statusCounts: statusSummary,
        totalNotional,
        filledNotional,
        latestUpdate,
      },
      rateLimit: {
        limit: rate.limit,
        remaining: rate.remaining,
      },
    });
  } catch (error) {
    logger.error({ err: error }, 'Failed to load trades');
    return NextResponse.json({ error: 'Failed to load trades' }, { status: 500 });
  }
}
