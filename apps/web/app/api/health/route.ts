import { NextResponse } from 'next/server';
import { createLogger, loadWebEnv } from '@trading-automation/shared';

const logger = createLogger({ name: 'web-health' });

export function GET() {
  const env = loadWebEnv();
  logger.debug({ env: env.NODE_ENV }, 'Health endpoint invoked');

  return NextResponse.json({
    status: 'ok',
    service: env.SERVICE_NAME,
    env: env.NODE_ENV,
    revalidateSeconds: env.NEXT_PUBLIC_REVALIDATE_SECONDS,
  });
}
