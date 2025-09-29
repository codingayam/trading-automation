import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { HttpRequestError } from '../../errors.js';
import type { Logger } from '../../logger.js';
import { QuiverClient } from '../client.js';

describe('QuiverClient', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  const createClient = (overrides: Partial<{ logger: Logger }> = {}) =>
    new QuiverClient({ apiKey: 'secret', baseUrl: 'https://api.quiverquant.com', ...overrides });

  it('sends Quiver Token authorization header', async () => {
    fetchMock.mockResolvedValue(new Response('[]', { status: 200 }));

    const client = createClient();

    await client.getCongressTradingByDate({ date: '2025-09-24' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] ?? [];
    const headers = init?.headers as Record<string, string> | undefined;

    expect(headers?.Authorization).toBe('Token secret');
    expect(headers?.Accept).toBe('application/json');
  });

  it('throws HttpRequestError when Quiver responds with 401', async () => {
    fetchMock.mockResolvedValue(new Response('Unauthorized', { status: 401, statusText: 'Unauthorized' }));

    const client = createClient();

    await expect(client.getCongressTradingByDate({ date: '2025-09-24' })).rejects.toBeInstanceOf(HttpRequestError);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('retries server errors before succeeding', async () => {
    fetchMock
      .mockResolvedValueOnce(new Response('{"error":"fail"}', { status: 500 }))
      .mockResolvedValueOnce(new Response('[]', { status: 200 }));

    const client = createClient();
    const result = await client.getCongressTradingByDate({ date: '2025-09-24' });

    expect(result).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('warns and returns empty list for unexpected payload shape', async () => {
    const warn = vi.fn();
    const logger = { warn } as unknown as Logger;

    fetchMock.mockResolvedValueOnce(new Response('{"unexpected":true}', { status: 200 }));

    const client = createClient({ logger });
    const result = await client.getCongressTradingByDate({ date: '2025-09-24' });

    expect(result).toEqual([]);
    expect(warn).toHaveBeenCalledWith(
      expect.objectContaining({ date: '20250924' }),
      'Unexpected Quiver response payload shape',
    );
  });
});
