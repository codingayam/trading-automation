import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AlpacaClient } from '../client.js';
import type { SubmitAlpacaOrderRequest } from '../types.js';

const baseOrder: SubmitAlpacaOrderRequest = {
  symbol: 'AAPL',
  qty: '1',
  side: 'buy',
  type: 'market',
  time_in_force: 'day',
};

const baseUrl = 'https://api.alpaca.markets';

describe('AlpacaClient', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  const createClient = () => new AlpacaClient({ key: 'key', secret: 'secret', baseUrl });

  it('sends auth headers when submitting orders', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ id: 'order-1' }), { status: 200 }));

    const client = createClient();
    await client.submitOrder(baseOrder);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    const headers = (init?.headers ?? {}) as Record<string, string>;

    expect(url).toBe(`${baseUrl}/v2/orders`);
    expect(init?.method).toBe('POST');
    expect(headers['APCA-API-KEY-ID']).toBe('key');
    expect(headers['APCA-API-SECRET-KEY']).toBe('secret');
    expect(headers['Content-Type']).toBe('application/json');
    expect(headers.Accept).toBe('application/json');
  });

  it('retries on transient server errors before succeeding', async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'server' }), { status: 500, statusText: 'Internal Server Error' }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'order-2' }), { status: 200 }));

    const client = createClient();
    const result = await client.submitOrder(baseOrder);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result).toEqual(expect.objectContaining({ id: 'order-2' }));

    const [firstCall, secondCall] = fetchMock.mock.calls;
    expect(firstCall?.[1]?.body).toBe(secondCall?.[1]?.body);
  });
});
