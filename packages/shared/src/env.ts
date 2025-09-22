import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { z } from 'zod';
import { EnvValidationError } from './errors';

const loadDotEnv = (() => {
  let loaded = false;

  const parseLine = (line: string): [string, string] | null => {
    const trimmed = line.trim();

    if (!trimmed || trimmed.startsWith('#')) {
      return null;
    }

    const withoutExport = trimmed.startsWith('export ')
      ? trimmed.slice('export '.length).trim()
      : trimmed;

    const eqIndex = withoutExport.indexOf('=');

    if (eqIndex <= 0) {
      return null;
    }

    const key = withoutExport.slice(0, eqIndex).trim();

    if (!key) {
      return null;
    }

    let value = withoutExport.slice(eqIndex + 1).trim();

    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    } else {
      const hashIndex = value.indexOf(' #');

      if (hashIndex !== -1) {
        value = value.slice(0, hashIndex);
      }

      value = value.trim();
    }

    value = value.replace(/\\n/g, '\n').replace(/\\r/g, '\r');

    return [key, value];
  };

  const applyEnvFile = (filePath: string): void => {
    const contents = readFileSync(filePath, 'utf8');

    for (const line of contents.split(/\r?\n/)) {
      const parsed = parseLine(line);

      if (!parsed) {
        continue;
      }

      const [key, value] = parsed;

      if (process.env[key] === undefined) {
        process.env[key] = value;
      }
    }
  };

  const findEnvFile = (): string | undefined => {
    if (typeof process === 'undefined' || typeof process.cwd !== 'function') {
      return undefined;
    }

    let current: string | undefined = process.cwd();

    while (current) {
      const candidate = resolve(current, '.env');

      if (existsSync(candidate)) {
        return candidate;
      }

      const parent = dirname(current);

      if (parent === current) {
        break;
      }

      current = parent;
    }

    return undefined;
  };

  return (): void => {
    if (loaded || typeof process === 'undefined' || process.release?.name !== 'node') {
      return;
    }

    const envFile = findEnvFile();

    if (envFile) {
      applyEnvFile(envFile);
    }

    loaded = true;
  };
})();

loadDotEnv();

type EnvTarget = 'worker' | 'web' | 'shared';

const booleanFromEnv = (defaultValue?: boolean) =>
  z.preprocess((value) => {
    if (value === undefined || value === null || value === '') {
      if (defaultValue !== undefined) {
        return defaultValue;
      }
      return value;
    }

    if (typeof value === 'boolean') {
      return value;
    }

    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase();
      if (['true', '1', 'yes', 'y', 'on'].includes(normalized)) {
        return true;
      }
      if (['false', '0', 'no', 'n', 'off'].includes(normalized)) {
        return false;
      }
    }

    return value;
  }, z.boolean());

const numberFromEnv = (options?: { defaultValue?: number; int?: boolean; positive?: boolean }) => {
  const { defaultValue, int, positive } = options ?? {};
  let schema = z.number();

  if (positive) {
    schema = schema.positive();
  }

  if (int) {
    schema = schema.int();
  }

  return z.preprocess((value) => {
    if (value === undefined || value === null || value === '') {
      if (defaultValue !== undefined) {
        return defaultValue;
      }
      return value;
    }

    if (typeof value === 'number') {
      return value;
    }

    if (typeof value === 'string') {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }

    return value;
  }, schema);
};

const optionalNumberFromEnv = (options?: { int?: boolean; positive?: boolean }) => {
  const { int, positive } = options ?? {};
  let schema = z.number();

  if (positive) {
    schema = schema.positive();
  }

  if (int) {
    schema = schema.int();
  }

  return z.preprocess((value) => {
    if (value === undefined || value === null || value === '') {
      return undefined;
    }

    if (typeof value === 'number') {
      return value;
    }

    if (typeof value === 'string') {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }

    return value;
  }, schema.optional());
};

const databasePoolModeEnum = z.enum(['direct', 'session', 'transaction']);

const baseSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace']).default('info'),
  SERVICE_NAME: z.string().min(1).default('trading-automation'),
});

const workerSchema = baseSchema.extend({
  DATABASE_URL: z.string().min(1, 'DATABASE_URL is required'),
  DIRECT_DATABASE_URL: z.string().min(1).optional(),
  DATABASE_POOL_MODE: databasePoolModeEnum.optional(),
  PRISMA_CONNECTION_LIMIT: optionalNumberFromEnv({ int: true, positive: true }),
  PRISMA_POOL_TIMEOUT_MS: optionalNumberFromEnv({ int: true, positive: true }),
  PRISMA_LOG_QUERIES: booleanFromEnv(false),
  ALPACA_KEY_ID: z.string().min(1, 'ALPACA_KEY_ID is required'),
  ALPACA_SECRET_KEY: z.string().min(1, 'ALPACA_SECRET_KEY is required'),
  ALPACA_BASE_URL: z
    .string()
    .url('ALPACA_BASE_URL must be a valid URL')
    .default('https://paper-api.alpaca.markets'),
  ALPACA_DATA_BASE_URL: z
    .string()
    .url('ALPACA_DATA_BASE_URL must be a valid URL')
    .default('https://data.alpaca.markets'),
  QUIVER_API_KEY: z.string().min(1, 'QUIVER_API_KEY is required'),
  QUIVER_BASE_URL: z
    .string()
    .url('QUIVER_BASE_URL must be a valid URL')
    .default('https://api.quiverquant.com/beta'),
  PAPER_TRADING: booleanFromEnv(true),
  TRADING_ENABLED: booleanFromEnv(true),
  TRADE_NOTIONAL_USD: numberFromEnv({ defaultValue: 1000, positive: true }),
  DAILY_MAX_FILINGS: optionalNumberFromEnv({ int: true, positive: true }),
  PER_TICKER_DAILY_MAX: optionalNumberFromEnv({ int: true, positive: true }),
});

const webSchema = baseSchema.extend({
  NEXT_PUBLIC_API_BASE_URL: z
    .string()
    .url('NEXT_PUBLIC_API_BASE_URL must be a valid URL')
    .optional(),
  NEXT_PUBLIC_REVALIDATE_SECONDS: numberFromEnv({ defaultValue: 60, int: true, positive: true }),
  PAPER_TRADING: booleanFromEnv(true),
  TRADING_ENABLED: booleanFromEnv(true),
  DATABASE_URL: z.string().min(1).optional(),
  DIRECT_DATABASE_URL: z.string().min(1).optional(),
  DATABASE_POOL_MODE: databasePoolModeEnum.optional(),
  PRISMA_CONNECTION_LIMIT: optionalNumberFromEnv({ int: true, positive: true }),
  PRISMA_POOL_TIMEOUT_MS: optionalNumberFromEnv({ int: true, positive: true }),
  PRISMA_LOG_QUERIES: booleanFromEnv(false),
});

const sharedSchema = baseSchema.extend({
  DATABASE_URL: z.string().min(1).optional(),
  DIRECT_DATABASE_URL: z.string().min(1).optional(),
  DATABASE_POOL_MODE: databasePoolModeEnum.optional(),
  PRISMA_CONNECTION_LIMIT: optionalNumberFromEnv({ int: true, positive: true }),
  PRISMA_POOL_TIMEOUT_MS: optionalNumberFromEnv({ int: true, positive: true }),
  PRISMA_LOG_QUERIES: booleanFromEnv(false),
  ALPACA_KEY_ID: z.string().min(1).optional(),
  ALPACA_SECRET_KEY: z.string().min(1).optional(),
  ALPACA_BASE_URL: z
    .string()
    .url('ALPACA_BASE_URL must be a valid URL')
    .default('https://paper-api.alpaca.markets'),
  ALPACA_DATA_BASE_URL: z
    .string()
    .url('ALPACA_DATA_BASE_URL must be a valid URL')
    .default('https://data.alpaca.markets'),
  TRADE_NOTIONAL_USD: numberFromEnv({ defaultValue: 1000, positive: true }),
});

type WorkerEnv = z.infer<typeof workerSchema>;
type WebEnv = z.infer<typeof webSchema>;
type SharedEnv = z.infer<typeof sharedSchema>;

const parseEnv = <Schema extends z.ZodTypeAny, Result = z.infer<Schema>>(
  schema: Schema,
  target: EnvTarget,
  overrides?: Record<string, unknown>,
): Readonly<Result> => {
  const merged = { ...process.env, ...overrides };
  const result = schema.safeParse(merged);

  if (!result.success) {
    throw new EnvValidationError({
      target,
      issues: result.error.issues,
    });
  }

  return Object.freeze(result.data) as Readonly<Result>;
};

export const loadWorkerEnv = (overrides?: Record<string, unknown>): Readonly<WorkerEnv> =>
  parseEnv(workerSchema, 'worker', overrides);

export const loadWebEnv = (overrides?: Record<string, unknown>): Readonly<WebEnv> =>
  parseEnv(webSchema, 'web', overrides);

export const loadSharedEnv = (overrides?: Record<string, unknown>): Readonly<SharedEnv> =>
  parseEnv(sharedSchema, 'shared', overrides);

export type { WorkerEnv, WebEnv, SharedEnv };
