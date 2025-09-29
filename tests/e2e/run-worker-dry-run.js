import process from 'node:process';
import { spawn } from 'node:child_process';

const REQUIRED_WORKER_ENV_KEYS = [
  'DATABASE_URL',
  'ALPACA_KEY_ID',
  'ALPACA_SECRET_KEY',
  'QUIVER_API_KEY',
];

const runCommand = (cmd, args, options) =>
  new Promise((resolve) => {
    const child = spawn(cmd, args, options);
    child.on('exit', (code) => resolve(code ?? 0));
    child.on('error', (error) => {
      // eslint-disable-next-line no-console
      console.error('worker-dry-run spawn failed', error);
      resolve(-1);
    });
  });

export const runWorkerDryRun = async () => {
  const missing = REQUIRED_WORKER_ENV_KEYS.filter((key) => !process.env[key]);

  if (missing.length > 0) {
    return {
      name: 'worker-dry-run',
      status: 'skipped',
      details: `Skipping worker dry-run; missing environment variables: ${missing.join(', ')}`,
    };
  }

  const args = ['--filter', '@trading-automation/worker', 'open-job', '--', '--dry-run'];
  const env = {
    ...process.env,
    TRADING_ENABLED: process.env.TRADING_ENABLED ?? 'false',
    LOG_LEVEL: process.env.LOG_LEVEL ?? 'info',
  };

  // eslint-disable-next-line no-console
  console.log('worker-dry-run: executing pnpm --filter @trading-automation/worker open-job -- --dry-run');

  const exitCode = await runCommand('pnpm', args, { stdio: 'inherit', env });

  if (exitCode !== 0) {
    return {
      name: 'worker-dry-run',
      status: 'failed',
      details: `Worker dry-run exited with code ${exitCode}`,
    };
  }

  return {
    name: 'worker-dry-run',
    status: 'passed',
    details: 'Dry-run completed successfully',
  };
};

if (import.meta.url === `file://${process.argv[1]}`) {
  runWorkerDryRun()
    .then((outcome) => {
      const message = `${outcome.name}: ${outcome.status.toUpperCase()}${outcome.details ? ` – ${outcome.details}` : ''}`;
      if (outcome.status === 'failed') {
        // eslint-disable-next-line no-console
        console.error(message);
        process.exitCode = 1;
      } else {
        // eslint-disable-next-line no-console
        console.log(message);
      }
    })
    .catch((error) => {
      // eslint-disable-next-line no-console
      console.error('worker-dry-run: FAILED', error);
      process.exitCode = 1;
    });
}
