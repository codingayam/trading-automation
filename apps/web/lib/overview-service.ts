import type { AlpacaAccount, AlpacaPosition } from '@trading-automation/shared';
import { createLogger, loadWebEnv } from '@trading-automation/shared';
import { getAlpacaClient } from './alpaca';
import { OFFLINE_ACCOUNT, OFFLINE_POSITIONS } from './offline-data';

const logger = createLogger({ name: 'overview-service' });

const toNumber = (value: string | number | null | undefined): number => {
  if (value === null || value === undefined) {
    return 0;
  }

  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isNaN(numeric) ? 0 : numeric;
};

export interface OverviewMetrics {
  portfolioValue: number;
  cash: number;
  buyingPower: number;
  totalCostBasis: number;
  totalUnrealizedPl: number;
  totalPlpc: number;
  investedSymbols: number;
}

export interface PositionBreakdownEntry {
  symbol: string;
  marketValue: number;
  costBasis: number;
  unrealizedPl: number;
  unrealizedPlpc: number;
}

export interface OverviewData {
  source: 'alpaca' | 'offline';
  fetchedAt: string;
  account: AlpacaAccount;
  positions: AlpacaPosition[];
  metrics: OverviewMetrics;
  breakdown: PositionBreakdownEntry[];
}

const computeMetrics = (account: AlpacaAccount, positions: AlpacaPosition[]): OverviewMetrics => {
  const portfolioValue = toNumber(account.portfolio_value);
  const cash = toNumber(account.cash);
  const buyingPower = toNumber(account.buying_power);

  const aggregates = positions.reduce(
    (acc, position) => {
      const costBasis = toNumber(position.cost_basis);
      const unrealizedPl = toNumber(position.unrealized_pl);

      acc.totalCostBasis += costBasis;
      acc.totalUnrealizedPl += unrealizedPl;

      return acc;
    },
    { totalCostBasis: 0, totalUnrealizedPl: 0 },
  );

  const totalPlpc = aggregates.totalCostBasis
    ? Number((aggregates.totalUnrealizedPl / aggregates.totalCostBasis).toFixed(4))
    : 0;

  return {
    portfolioValue,
    cash,
    buyingPower,
    totalCostBasis: Number(aggregates.totalCostBasis.toFixed(2)),
    totalUnrealizedPl: Number(aggregates.totalUnrealizedPl.toFixed(2)),
    totalPlpc,
    investedSymbols: positions.length,
  } satisfies OverviewMetrics;
};

const buildBreakdown = (positions: AlpacaPosition[]): PositionBreakdownEntry[] =>
  positions
    .map((position) => ({
      symbol: position.symbol,
      marketValue: toNumber(position.market_value),
      costBasis: toNumber(position.cost_basis),
      unrealizedPl: toNumber(position.unrealized_pl),
      unrealizedPlpc: Number(toNumber(position.unrealized_plpc).toFixed(4)),
    }))
    .sort((a, b) => b.marketValue - a.marketValue);

export const fetchOverviewData = async (): Promise<OverviewData> => {
  const client = getAlpacaClient();

  if (!client) {
    const fallbackPositions = [...OFFLINE_POSITIONS];
    return {
      source: 'offline',
      fetchedAt: new Date().toISOString(),
      account: OFFLINE_ACCOUNT,
      positions: fallbackPositions,
      metrics: computeMetrics(OFFLINE_ACCOUNT, fallbackPositions),
      breakdown: buildBreakdown(fallbackPositions),
    } satisfies OverviewData;
  }

  try {
    const [account, positions] = await Promise.all([client.getAccount(), client.getPositions()]);

    return {
      source: 'alpaca',
      fetchedAt: new Date().toISOString(),
      account,
      positions,
      metrics: computeMetrics(account, positions),
      breakdown: buildBreakdown(positions),
    } satisfies OverviewData;
  } catch (error) {
    logger.error({ err: error }, 'Failed to fetch Alpaca data, falling back to offline seed');
    const fallbackPositions = [...OFFLINE_POSITIONS];

    return {
      source: 'offline',
      fetchedAt: new Date().toISOString(),
      account: OFFLINE_ACCOUNT,
      positions: fallbackPositions,
      metrics: computeMetrics(OFFLINE_ACCOUNT, fallbackPositions),
      breakdown: buildBreakdown(fallbackPositions),
    } satisfies OverviewData;
  }
};

export const fetchPositionsOnly = async (): Promise<{
  source: 'alpaca' | 'offline';
  positions: AlpacaPosition[];
  fetchedAt: string;
}> => {
  const client = getAlpacaClient();

  if (!client) {
    return {
      source: 'offline',
      fetchedAt: new Date().toISOString(),
      positions: [...OFFLINE_POSITIONS],
    };
  }

  try {
    const positions = await client.getPositions();
    return {
      source: 'alpaca',
      fetchedAt: new Date().toISOString(),
      positions,
    };
  } catch (error) {
    logger.error({ err: error }, 'Failed to fetch Alpaca positions, using offline data');
    return {
      source: 'offline',
      fetchedAt: new Date().toISOString(),
      positions: [...OFFLINE_POSITIONS],
    };
  }
};

export const getRevalidateSeconds = (): number => loadWebEnv().NEXT_PUBLIC_REVALIDATE_SECONDS;
