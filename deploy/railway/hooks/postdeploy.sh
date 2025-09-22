#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm must be available in Railway build image" >&2
  exit 1
fi

echo "[railway] Installing dependencies with frozen lockfile"
CI=${CI:-true} pnpm install --frozen-lockfile

echo "[railway] Regenerating Prisma client"
pnpm run prisma:generate

echo "[railway] Applying migrations"
pnpm run migrate

echo "[railway] Post-deploy hook complete"
