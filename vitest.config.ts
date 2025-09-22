import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: rootDir,
  test: {
    globals: true,
    environment: 'node',
    include: [
      'packages/shared/src/**/*.test.ts',
      'apps/worker/src/**/*.test.ts',
      'apps/web/src/**/*.test.ts',
      'apps/web/app/**/*.test.tsx',
    ],
    coverage: {
      enabled: false,
    },
    passWithNoTests: true,
  },
  resolve: {
    alias: {
      '@trading-automation/shared': path.resolve(rootDir, 'packages/shared/src'),
    },
  },
});
