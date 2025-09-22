import { fetchPositionsOnly, getRevalidateSeconds } from '../../lib/overview-service';
import { formatCurrency, formatNumber, formatPercent } from '../../lib/format';
import { DataTable } from '../../components/ui';

export const revalidate = getRevalidateSeconds();

const toNumber = (value: string): number => {
  const numeric = Number(value);
  return Number.isNaN(numeric) ? 0 : numeric;
};

export default async function PositionsPage() {
  const { positions, source, fetchedAt } = await fetchPositionsOnly();

  const rows = positions.map((position) => ({
    symbol: position.symbol,
    side: position.side,
    qty: toNumber(position.qty),
    marketValue: toNumber(position.market_value),
    costBasis: toNumber(position.cost_basis),
    unrealizedPl: toNumber(position.unrealized_pl),
    unrealizedPlpc: Number(toNumber(position.unrealized_plpc).toFixed(4)),
    currentPrice: toNumber(position.current_price),
    changeToday: Number(toNumber(position.change_today).toFixed(4)),
  }));

  return (
    <section style={{ padding: '2rem 1.5rem', maxWidth: '960px', margin: '0 auto', width: '100%' }}>
      <header style={{ marginBottom: '2rem' }}>
        <p style={{ color: '#94a3b8', fontSize: '0.8rem', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          Live Positions
        </p>
        <h1 style={{ fontSize: '2rem', margin: '0.25rem 0 0.5rem' }}>Alpaca holdings</h1>
        <p style={{ color: '#cbd5f5', maxWidth: '680px' }}>
          Fetched directly from Alpaca using the shared client wrapper. Data refreshes every {revalidate} seconds on the
          server and never touches the database layer.
        </p>
        <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
          Source: {source === 'alpaca' ? 'Live Alpaca API' : 'Offline seed'} · Last refreshed {new Date(fetchedAt).toLocaleString()}
        </p>
      </header>

      <DataTable
        caption="Positions streamed from Alpaca"
        columns={[
          {
            key: 'symbol',
            header: 'Symbol',
            accessor: (row: (typeof rows)[number]) => (
              <span style={{ fontWeight: 600 }}>{row.symbol}</span>
            ),
          },
          {
            key: 'side',
            header: 'Side',
            accessor: (row) => row.side,
          },
          {
            key: 'qty',
            header: 'Quantity',
            accessor: (row) => formatNumber(row.qty),
          },
          {
            key: 'price',
            header: 'Last Price',
            accessor: (row) => formatCurrency(row.currentPrice),
            align: 'right',
          },
          {
            key: 'marketValue',
            header: 'Market Value',
            accessor: (row) => formatCurrency(row.marketValue),
            align: 'right',
          },
          {
            key: 'unrealizedPl',
            header: 'Unrealized P/L',
            render: (row) => (
              <span style={{ color: row.unrealizedPl >= 0 ? '#22c55e' : '#f87171', fontWeight: 600 }}>
                {formatCurrency(row.unrealizedPl)}
              </span>
            ),
            align: 'right',
          },
          {
            key: 'unrealizedPlpc',
            header: 'Return %',
            render: (row) => (
              <span style={{ color: row.unrealizedPl >= 0 ? '#22c55e' : '#f87171' }}>
                {formatPercent(row.unrealizedPlpc)}
              </span>
            ),
            align: 'right',
          },
          {
            key: 'changeToday',
            header: 'Change Today',
            render: (row) => (
              <span style={{ color: row.changeToday >= 0 ? '#38bdf8' : '#f87171' }}>
                {formatPercent(row.changeToday)}
              </span>
            ),
            align: 'right',
          },
        ]}
        data={rows}
        emptyState={<p style={{ margin: 0, color: '#94a3b8' }}>No active positions detected at this time.</p>}
      />
    </section>
  );
}
