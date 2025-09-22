import { createLogger, loadWorkerEnv } from '@trading-automation/shared';

const fallbackLogger = createLogger({ name: 'worker-bootstrap' });

async function main(): Promise<void> {
  const env = loadWorkerEnv();
  const logger = createLogger({
    name: env.SERVICE_NAME ?? 'open-job-worker',
    level: env.LOG_LEVEL,
    base: {
      service: env.SERVICE_NAME,
      env: env.NODE_ENV,
    },
  });

  logger.info('Starting Congress-Mirror open-job worker (no-op stub)');

  logger.info(
    {
      tradingEnabled: env.TRADING_ENABLED,
      paperTrading: env.PAPER_TRADING,
      alpacaBaseUrl: env.ALPACA_BASE_URL,
    },
    'No-op worker run complete; awaiting downstream integrations',
  );
}

main().catch((error) => {
  fallbackLogger.error({ err: error }, 'Worker entrypoint failed');
  process.exitCode = 1;
});
