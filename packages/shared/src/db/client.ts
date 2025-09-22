import { PrismaClient, type Prisma } from '@prisma/client';
import { loadSharedEnv } from '../env';
import { createLogger } from '../logger';

const prismaLogger = createLogger({ name: 'prisma' });

const buildDatasourceUrl = (
  envUrl: string,
  options: { poolMode?: 'direct' | 'session' | 'transaction'; connectionLimit?: number; poolTimeoutMs?: number },
) => {
  const { poolMode = 'direct', connectionLimit, poolTimeoutMs } = options;

  try {
    const url = new URL(envUrl);

    if (poolMode !== 'direct') {
      url.searchParams.set('pgbouncer', 'true');
      url.searchParams.set('connection_limit', String(connectionLimit ?? 1));
      if (poolTimeoutMs) {
        url.searchParams.set('pool_timeout', String(poolTimeoutMs));
      }
    } else {
      if (connectionLimit) {
        url.searchParams.set('connection_limit', String(connectionLimit));
      }
      if (poolTimeoutMs) {
        url.searchParams.set('pool_timeout', String(poolTimeoutMs));
      }
    }

    return url.toString();
  } catch (error) {
    prismaLogger.warn({ err: error }, 'Failed to parse DATABASE_URL, falling back to provided value');
    return envUrl;
  }
};

const createClient = (): PrismaClient => {
  const env = loadSharedEnv();
  const { DATABASE_URL, DATABASE_POOL_MODE, PRISMA_CONNECTION_LIMIT, PRISMA_POOL_TIMEOUT_MS, PRISMA_LOG_QUERIES } = env;

  if (!DATABASE_URL) {
    throw new Error('DATABASE_URL must be defined to instantiate PrismaClient');
  }

  const poolMode = DATABASE_POOL_MODE ?? 'direct';
  const datasourceUrl = buildDatasourceUrl(DATABASE_URL, {
    poolMode,
    connectionLimit: PRISMA_CONNECTION_LIMIT,
    poolTimeoutMs: PRISMA_POOL_TIMEOUT_MS,
  });

  const logLevels: Prisma.LogLevel[] = ['error', 'warn'];
  const logDefinitions: Prisma.LogDefinition[] = PRISMA_LOG_QUERIES
    ? [{ level: 'query', emit: 'event' }]
    : [];

  const prisma = new PrismaClient({
    datasources: {
      db: {
        url: datasourceUrl,
      },
    },
    log: [...logLevels, ...logDefinitions],
  });

  if (PRISMA_LOG_QUERIES) {
    prisma.$on('query', (event) => {
      prismaLogger.debug(
        {
          query: event.query,
          params: event.params,
          durationMs: event.duration,
        },
        'Prisma query executed',
      );
    });
  }

  return prisma;
};

const globalForPrisma = globalThis as typeof globalThis & {
  __prismaClient?: PrismaClient;
};

export const prisma: PrismaClient = globalForPrisma.__prismaClient ?? createClient();

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.__prismaClient = prisma;
}

export const getPrismaClient = (): PrismaClient => prisma;

export const disconnectPrisma = async (): Promise<void> => {
  if (globalForPrisma.__prismaClient) {
    await globalForPrisma.__prismaClient.$disconnect();
    if (process.env.NODE_ENV !== 'production') {
      globalForPrisma.__prismaClient = undefined;
    }
  } else {
    await prisma.$disconnect();
  }
};
