import {
  createLogger,
  disconnectPrisma,
  loadWorkerEnv,
  parseQuiverDate,
  startOfEasternDay,
} from '@trading-automation/shared';

import { runOpenJob } from './open-job-runner.js';

const fallbackLogger = createLogger({ name: 'worker-bootstrap' });

interface CliFlags {
  dryRun: boolean;
  force: boolean;
  tradingDateOverride?: Date;
}

const parseCliFlags = (argv: string[]): CliFlags => {
  let dryRun = false;
  let force = false;
  let tradingDateOverride: Date | undefined;

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === '--dry-run' || arg === '-d') {
      dryRun = true;
      continue;
    }

    if (arg === '--force' || arg === '-f') {
      force = true;
      continue;
    }

    if (arg.startsWith('--dry-run=')) {
      const value = arg.split('=')[1];
      dryRun = value !== 'false';
      continue;
    }

    if (arg.startsWith('--force=')) {
      const value = arg.split('=')[1];
      force = value !== 'false';
      continue;
    }

    if (arg === '--trading-date' || arg === '-t') {
      const value = argv[index + 1];
      if (!value) {
        throw new Error('Missing value for --trading-date flag');
      }
      index += 1;
      const parsed = parseQuiverDate(value);
      if (!parsed) {
        throw new Error(`Invalid trading date value: ${value}`);
      }
      tradingDateOverride = startOfEasternDay(parsed);
      continue;
    }

    if (arg.startsWith('--trading-date=')) {
      const value = arg.split('=')[1];
      if (!value) {
        throw new Error('Invalid --trading-date flag; expected a value');
      }
      const parsed = parseQuiverDate(value);
      if (!parsed) {
        throw new Error(`Invalid trading date value: ${value}`);
      }
      tradingDateOverride = startOfEasternDay(parsed);
    }
  }

  return { dryRun, force, tradingDateOverride };
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

  logger.info(
    {
      dryRun: flags.dryRun,
      force: flags.force,
      tradingDateOverride: flags.tradingDateOverride?.toISOString() ?? null,
    },
    'Starting Congress-Mirror open-job worker',
  );

  const result = await runOpenJob({
    env,
    logger,
    dryRun: flags.dryRun,
    overrideTradingDate: flags.tradingDateOverride,
    force: flags.force,
  });

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
