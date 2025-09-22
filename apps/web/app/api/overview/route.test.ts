import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import * as rateLimit from '../../../lib/rate-limit';
import { setAlpacaClientForTesting, resetAlpacaClient } from '../../../lib/alpaca';
import { OFFLINE_ACCOUNT, OFFLINE_POSITIONS } from '../../../lib/offline-data';
import { GET } from './route';

process.env.NEXT_PUBLIC_REVALIDATE_SECONDS ??= '60';
process.env.NODE_ENV = 'test';

let rateLimitSpy: ReturnType<typeof vi.spyOn<typeof rateLimit, 'applyRateLimit'>>;

describe('GET /api/overview', () => {
  beforeEach(() => {
    rateLimitSpy = vi.spyOn(rateLimit, 'applyRateLimit').mockReturnValue({ allowed: true, remaining: 9, limit: 10 });
    setAlpacaClientForTesting(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetAlpacaClient();
  });

  it('returns offline overview when Alpaca client is not configured', async () => {
    const overviewModule = await import('../../../lib/overview-service');
    const fetchSpy = vi.spyOn(overviewModule, 'fetchOverviewData');
    fetchSpy.mockResolvedValue({
      source: 'offline',
      fetchedAt: new Date().toISOString(),
      account: OFFLINE_ACCOUNT,
      positions: OFFLINE_POSITIONS,
      metrics: {
        portfolioValue: 18500,
        cash: 5000,
        buyingPower: 25000,
        totalCostBasis: 6778,
        totalUnrealizedPl: 530,
        totalPlpc: 0.08,
        investedSymbols: OFFLINE_POSITIONS.length,
      },
      breakdown: OFFLINE_POSITIONS.map((position) => ({
        symbol: position.symbol,
        marketValue: Number(position.market_value),
        costBasis: Number(position.cost_basis),
        unrealizedPl: Number(position.unrealized_pl),
        unrealizedPlpc: Number(position.unrealized_plpc),
      })),
    });

    const request = new NextRequest(new URL('http://localhost/api/overview'));
    const response = await GET(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.source).toBe('offline');
    expect(body.metrics.investedSymbols).toBe(OFFLINE_POSITIONS.length);
  });

  it('returns 429 when rate limit exceeded', async () => {
    rateLimitSpy.mockReturnValueOnce({ allowed: false, remaining: 0, limit: 1, retryAfterMs: 2000 });

    const request = new NextRequest(new URL('http://localhost/api/overview'));
    const response = await GET(request);
    expect(response.status).toBe(429);
    const body = await response.json();
    expect(body.error).toContain('Rate limit');
  });
});
