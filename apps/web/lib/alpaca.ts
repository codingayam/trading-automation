import { createLogger, createAlpacaClient, loadSharedEnv, type AlpacaClient } from '@trading-automation/shared';

let cachedClient: AlpacaClient | null | undefined;

const resolveCredentials = () => {
  const key = process.env.ALPACA_KEY_ID ?? undefined;
  const secret = process.env.ALPACA_SECRET_KEY ?? undefined;

  if (key && secret) {
    return { key, secret };
  }

  const env = loadSharedEnv();

  if (env.ALPACA_KEY_ID && env.ALPACA_SECRET_KEY) {
    return { key: env.ALPACA_KEY_ID, secret: env.ALPACA_SECRET_KEY };
  }

  return undefined;
};

export const getAlpacaClient = (): AlpacaClient | null => {
  if (cachedClient !== undefined) {
    return cachedClient;
  }

  const credentials = resolveCredentials();

  if (!credentials) {
    cachedClient = null;
    return cachedClient;
  }

  const env = loadSharedEnv();

  cachedClient = createAlpacaClient({
    key: credentials.key,
    secret: credentials.secret,
    baseUrl: env.ALPACA_BASE_URL,
    dataBaseUrl: env.ALPACA_DATA_BASE_URL,
    logger: createLogger({ name: 'alpaca-client' }),
  });

  return cachedClient;
};

export const resetAlpacaClient = (): void => {
  cachedClient = undefined;
};

export const setAlpacaClientForTesting = (client: AlpacaClient | null): void => {
  cachedClient = client;
};
