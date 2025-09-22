import { describe, expect, it } from 'vitest';
import { loadSharedEnv, loadWebEnv, loadWorkerEnv } from './env';
import { EnvValidationError } from './errors';

describe('environment loader', () => {
  const baseWorkerEnv = {
    NODE_ENV: 'test',
    DATABASE_URL: 'postgresql://postgres:postgres@localhost:5432/trading',
    ALPACA_KEY_ID: 'key',
    ALPACA_SECRET_KEY: 'secret',
    QUIVER_API_KEY: 'quiver-key',
  } satisfies Record<string, unknown>;

  it('parses worker environment with defaults applied', () => {
    const env = loadWorkerEnv(baseWorkerEnv);

    expect(env.NODE_ENV).toBe('test');
    expect(env.PAPER_TRADING).toBe(true);
    expect(env.TRADE_NOTIONAL_USD).toBe(1000);
    expect(env.QUIVER_BASE_URL).toBe('https://api.quiverquant.com/beta');
  });

  it('coerces numeric values and honours optional guards', () => {
    const env = loadWorkerEnv({
      ...baseWorkerEnv,
      TRADE_NOTIONAL_USD: '1500',
      DAILY_MAX_FILINGS: '50',
      PER_TICKER_DAILY_MAX: 20,
      PAPER_TRADING: 'false',
    });

    expect(env.TRADE_NOTIONAL_USD).toBe(1500);
    expect(env.DAILY_MAX_FILINGS).toBe(50);
    expect(env.PER_TICKER_DAILY_MAX).toBe(20);
    expect(env.PAPER_TRADING).toBe(false);
  });

  it('throws when required worker env vars are missing', () => {
    expect(() =>
      loadWorkerEnv({
        ...baseWorkerEnv,
        ALPACA_KEY_ID: undefined,
      }),
    ).toThrow(EnvValidationError);
  });

  it('parses shared env without requiring service-specific vars', () => {
    const env = loadSharedEnv({ NODE_ENV: 'development' });

    expect(env.TRADE_NOTIONAL_USD).toBe(1000);
    expect(env.ALPACA_BASE_URL).toBe('https://paper-api.alpaca.markets');
  });

  it('parses web env and applies defaults', () => {
    const env = loadWebEnv({ NODE_ENV: 'development' });

    expect(env.NEXT_PUBLIC_REVALIDATE_SECONDS).toBe(60);
    expect(env.PAPER_TRADING).toBe(true);
  });
});
