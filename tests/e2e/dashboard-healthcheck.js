import process from 'node:process';

const HEALTHCHECK_ENV_VAR = 'E2E_HEALTHCHECK_URL';

export const runDashboardHealthcheck = async () => {
  const urlFromEnv = process.env[HEALTHCHECK_ENV_VAR];

  if (!urlFromEnv) {
    return {
      name: 'dashboard-healthcheck',
      status: 'skipped',
      details: `Set ${HEALTHCHECK_ENV_VAR} to run the dashboard healthcheck`,
    };
  }

  const healthUrl = urlFromEnv.endsWith('/health') ? urlFromEnv : `${urlFromEnv.replace(/\/$/, '')}/api/health`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);

  try {
    const response = await fetch(healthUrl, { signal: controller.signal });
    clearTimeout(timeout);

    if (!response.ok) {
      const body = await response.text().catch(() => '');
      return {
        name: 'dashboard-healthcheck',
        status: 'failed',
        details: `Healthcheck responded with ${response.status} ${response.statusText} ${body}`,
      };
    }

    return {
      name: 'dashboard-healthcheck',
      status: 'passed',
      details: `Healthcheck responded with ${response.status}`,
    };
  } catch (error) {
    clearTimeout(timeout);
    return {
      name: 'dashboard-healthcheck',
      status: 'failed',
      details: `Healthcheck request failed: ${(error instanceof Error ? error.message : String(error))}`,
    };
  }
};

if (import.meta.url === `file://${process.argv[1]}`) {
  runDashboardHealthcheck()
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
      console.error('dashboard-healthcheck: FAILED', error);
      process.exitCode = 1;
    });
}
