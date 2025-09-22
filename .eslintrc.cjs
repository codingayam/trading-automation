module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint'],
  extends: ['eslint:recommended', 'plugin:@typescript-eslint/recommended', 'next/core-web-vitals', 'prettier'],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    project: './tsconfig.eslint.json',
    tsconfigRootDir: __dirname,
  },
  settings: {
    next: {
      rootDir: ['apps/web'],
    },
  },
  ignorePatterns: ['**/dist/**', '**/.next/**', '**/node_modules/**'],
  rules: {
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-floating-promises': 'error',
  },
};
