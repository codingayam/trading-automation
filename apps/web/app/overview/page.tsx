import { Suspense } from 'react';
import { fetchOverviewData, getRevalidateSeconds } from '../../lib/overview-service';
import { formatCurrency, formatNumber, formatPercent } from '../../lib/format';
import { MetricCard, DataTable } from '../../components/ui';
import { PortfolioDistributionChart } from '../../components/overview/portfolio-distribution-chart';

export const revalidate = getRevalidateSeconds();

const toNumber = (value: string): number => {
  const numeric = Number(value);
  return Number.isNaN(numeric) ? 0 : numeric;
};

export default async function OverviewPage() {
  const overview = await fetchOverviewData();

  const topPositions = overview.positions.map((position) => ({
    symbol: position.symbol,
    qty: toNumber(position.qty),
    marketValue: toNumber(position.market_value),
    costBasis: toNumber(position.cost_basis),
    unrealizedPl: toNumber(position.unrealized_pl),
    unrealizedPlpc: Number(toNumber(position.unrealized_plpc).toFixed(4)),
    changeToday: Number(toNumber(position.change_today).toFixed(4)),
    currentPrice: toNumber(position.current_price),
  }));

  const dataSourceLabel = overview.source === 'alpaca' ? 'Live Alpaca' : 'Offline Seed';

  return (
    <section style={{ padding: '2rem 1.5rem', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      <header style={{ marginBottom: '2rem' }}>
        <p style={{ color: '#94a3b8', fontSize: '0.8rem', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          Portfolio Overview
        </p>
        <h1 style={{ fontSize: '2.25rem', margin: '0.25rem 0 0.5rem' }}>Performance snapshot</h1>
        <p style={{ color: '#cbd5f5', maxWidth: '720px' }}>
          Metrics update every {revalidate} seconds using {dataSourceLabel} data. Offline mode leverages seed fixtures so
          you can build UI flows before Alpaca credentials are wired.
        </p>
        <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Last refreshed: {new Date(overview.fetchedAt).toLocaleString()}</p>
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2rem',
        }}
      >
        <MetricCard title="Portfolio Value" value={formatCurrency(overview.metrics.portfolioValue)} subtitle={dataSourceLabel} />
        <MetricCard
          title="Total Unrealized P/L"
          value={formatCurrency(overview.metrics.totalUnrealizedPl)}
          description={`Overall change of ${formatPercent(overview.metrics.totalPlpc)}`}
          accent={overview.metrics.totalUnrealizedPl >= 0 ? 'success' : 'danger'}
        />
        <MetricCard
          title="Cost Basis"
          value={formatCurrency(overview.metrics.totalCostBasis)}
          description="Capital deployed across open positions"
        />
        <MetricCard
          title="Cash & Buying Power"
          value={formatCurrency(overview.metrics.cash)}
          description={`Buying power ${formatCurrency(overview.metrics.buyingPower)}`}
        />
        <MetricCard
          title="Active Symbols"
          value={formatNumber(overview.metrics.investedSymbols)}
          description="Distinct tickers currently held"
        />
      </div>

      <section style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        <div
          style={{
            background: '#111827',
            borderRadius: '0.75rem',
            padding: '1.5rem',
            border: '1px solid rgba(148, 163, 184, 0.35)',
          }}
        >
          <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.25rem' }}>Allocation by Symbol</h2>
          <p style={{ margin: '0 0 1.5rem', color: '#94a3b8', fontSize: '0.9rem' }}>
            Visualise market value, cost basis, and unrealised performance across your active holdings.
          </p>
          <Suspense fallback={<p style={{ color: '#94a3b8' }}>Rendering chart…</p>}>
            <PortfolioDistributionChart data={overview.breakdown} />
          </Suspense>
        </div>
      </section>

      <section>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>Open Positions</h2>
        <DataTable
          caption="Live positions returned from Alpaca"
          columns={[
            {
              key: 'symbol',
              header: 'Symbol',
              accessor: (position: (typeof topPositions)[number]) => (
                <strong style={{ fontSize: '0.95rem' }}>{position.symbol}</strong>
              ),
            },
            {
              key: 'qty',
              header: 'Quantity',
              accessor: (position) => formatNumber(position.qty),
            },
            {
              key: 'marketValue',
              header: 'Market Value',
              accessor: (position) => formatCurrency(position.marketValue),
              align: 'right',
            },
            {
              key: 'costBasis',
              header: 'Cost Basis',
              accessor: (position) => formatCurrency(position.costBasis),
              align: 'right',
            },
            {
              key: 'unrealizedPl',
              header: 'Unrealized P/L',
              render: (position) => (
                <span style={{ color: position.unrealizedPl >= 0 ? '#22c55e' : '#f87171', fontWeight: 600 }}>
                  {formatCurrency(position.unrealizedPl)}
                </span>
              ),
              align: 'right',
            },
            {
              key: 'unrealizedPlpc',
              header: 'Return %',
              render: (position) => (
                <span style={{ color: position.unrealizedPl >= 0 ? '#22c55e' : '#f87171' }}>
                  {formatPercent(position.unrealizedPlpc)}
                </span>
              ),
              align: 'right',
            },
            {
              key: 'changeToday',
              header: 'Change Today',
              render: (position) => (
                <span style={{ color: position.changeToday >= 0 ? '#38bdf8' : '#f87171' }}>
                  {formatPercent(position.changeToday)}
                </span>
              ),
              align: 'right',
            },
          ]}
          data={topPositions}
          emptyState={<p style={{ margin: 0, color: '#94a3b8' }}>No active positions found.</p>}
        />
      </section>
    </section>
  );
}
