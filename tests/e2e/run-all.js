import process from 'node:process';

import { runWorkerDryRun } from './run-worker-dry-run.js';
import { runDashboardHealthcheck } from './dashboard-healthcheck.js';

const steps = [runWorkerDryRun, runDashboardHealthcheck];

const run = async () => {
  const results = [];

  for (const step of steps) {
    try {
      const result = await step();
      results.push(result);
      const output = `${result.name}: ${result.status.toUpperCase()}${result.details ? ` – ${result.details}` : ''}`;
      if (result.status === 'failed') {
        // eslint-disable-next-line no-console
        console.error(output);
      } else {
        // eslint-disable-next-line no-console
        console.log(output);
      }
    } catch (error) {
      const message = `${step.name || 'unknown-step'}: FAILED – ${(error instanceof Error ? error.message : String(error))}`;
      results.push({ name: step.name || 'unknown-step', status: 'failed', details: message });
      // eslint-disable-next-line no-console
      console.error(message);
    }
  }

  if (results.some((result) => result.status === 'failed')) {
    process.exitCode = 1;
  }
};

run().catch((error) => {
  // eslint-disable-next-line no-console
  console.error('e2e runner failed unexpectedly', error);
  process.exitCode = 1;
});
