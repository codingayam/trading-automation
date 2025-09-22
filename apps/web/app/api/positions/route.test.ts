import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import * as rateLimit from '../../../lib/rate-limit';
import { setAlpacaClientForTesting, resetAlpacaClient } from '../../../lib/alpaca';
import { OFFLINE_POSITIONS } from '../../../lib/offline-data';
import { GET } from './route';

process.env.NEXT_PUBLIC_REVALIDATE_SECONDS ??= '60';
process.env.NODE_ENV = 'test';

let rateLimitSpy: ReturnType<typeof vi.spyOn<typeof rateLimit, 'applyRateLimit'>>;

describe('GET /api/positions', () => {
  beforeEach(() => {
    rateLimitSpy = vi.spyOn(rateLimit, 'applyRateLimit').mockReturnValue({ allowed: true, remaining: 9, limit: 10 });
    setAlpacaClientForTesting(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetAlpacaClient();
  });

  it('returns positions with offline fallback when Alpaca unavailable', async () => {
    const overviewModule = await import('../../../lib/overview-service');
    vi.spyOn(overviewModule, 'fetchPositionsOnly').mockResolvedValue({
      source: 'offline',
      fetchedAt: new Date().toISOString(),
      positions: OFFLINE_POSITIONS,
    });

    const request = new NextRequest(new URL('http://localhost/api/positions'));
    const response = await GET(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.positions).toHaveLength(OFFLINE_POSITIONS.length);
    expect(body.source).toBe('offline');
  });

  it('returns 429 when rate limiter blocks the request', async () => {
    rateLimitSpy.mockReturnValueOnce({ allowed: false, remaining: 0, limit: 1, retryAfterMs: 1000 });

    const request = new NextRequest(new URL('http://localhost/api/positions'));
    const response = await GET(request);

    expect(response.status).toBe(429);
    expect(await response.json()).toMatchObject({ error: expect.stringContaining('Rate limit') });
  });
});
