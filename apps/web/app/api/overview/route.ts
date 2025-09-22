import { NextResponse, type NextRequest } from 'next/server';
import { createLogger } from '@trading-automation/shared';
import { fetchOverviewData, getRevalidateSeconds } from '../../../lib/overview-service';
import { applyRateLimit } from '../../../lib/rate-limit';
import { getClientAddress } from '../../../lib/request';

const logger = createLogger({ name: 'api-overview' });

export const revalidate = getRevalidateSeconds();

export async function GET(request: NextRequest) {
  const address = getClientAddress(request);
  const rate = applyRateLimit(`overview:${address}`);

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

  try {
    const data = await fetchOverviewData();
    const cacheHeader = `s-maxage=${revalidate}, stale-while-revalidate=${Math.max(15, Math.round(revalidate / 2))}`;

    return NextResponse.json(
      { ...data, rateLimit: { limit: rate.limit, remaining: rate.remaining } },
      {
        status: 200,
        headers: {
          'Cache-Control': cacheHeader,
        },
      },
    );
  } catch (error) {
    logger.error({ err: error }, 'Failed to build overview payload');

    return NextResponse.json(
      { error: 'Failed to load overview data' },
      {
        status: 500,
      },
    );
  }
}
