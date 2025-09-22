import { createLogger, disconnectPrisma, loadWorkerEnv } from '@trading-automation/shared';

import { runOpenJob } from './open-job-runner';

const fallbackLogger = createLogger({ name: 'worker-bootstrap' });

interface CliFlags {
  dryRun: boolean;
}

const parseCliFlags = (argv: string[]): CliFlags => {
  const dryRun = argv.includes('--dry-run') || argv.includes('-d');
  return { dryRun };
};

async function main(): Promise<void> {
  const flags = parseCliFlags(process.argv.slice(2));
  const env = loadWorkerEnv();
  const logger = createLogger({
    name: env.SERVICE_NAME ?? 'open-job-worker',
    level: env.LOG_LEVEL,
    base: {
      service: env.SERVICE_NAME,
      env: env.NODE_ENV,
      dryRun: flags.dryRun,
    },
  });

  logger.info({ dryRun: flags.dryRun }, 'Starting Congress-Mirror open-job worker');

  const result = await runOpenJob({ env, logger, dryRun: flags.dryRun });

  if (result.status === 'failed') {
    process.exitCode = 1;
    logger.error({ summary: result.summary }, 'Open-job worker failed');
    return;
  }

  logger.info({ status: result.status, summary: result.summary }, 'Open-job worker completed');
}

main()
  .catch((error) => {
    fallbackLogger.error({ err: error }, 'Worker entrypoint failed');
    process.exitCode = 1;
  })
  .finally(async () => {
    try {
      await disconnectPrisma();
    } catch (error) {
      fallbackLogger.error({ err: error }, 'Failed to disconnect Prisma client');
    }
  });
