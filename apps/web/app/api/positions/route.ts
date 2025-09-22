import { NextResponse, type NextRequest } from 'next/server';
import { createLogger } from '@trading-automation/shared';
import { fetchPositionsOnly, getRevalidateSeconds } from '../../../lib/overview-service';
import { applyRateLimit } from '../../../lib/rate-limit';
import { getClientAddress } from '../../../lib/request';

const logger = createLogger({ name: 'api-positions' });

export const revalidate = getRevalidateSeconds();

export async function GET(request: NextRequest) {
  const address = getClientAddress(request);
  const rate = applyRateLimit(`positions:${address}`);

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
    const data = await fetchPositionsOnly();
    const cacheHeader = `s-maxage=${revalidate}, stale-while-revalidate=${Math.max(15, Math.round(revalidate / 2))}`;

    return NextResponse.json(
      { ...data, rateLimit: { limit: rate.limit, remaining: rate.remaining } },
      {
        headers: {
          'Cache-Control': cacheHeader,
        },
      },
    );
  } catch (error) {
    logger.error({ err: error }, 'Failed to load positions');
    return NextResponse.json({ error: 'Failed to load positions' }, { status: 500 });
  }
}
