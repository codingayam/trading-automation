import Link from 'next/link';
import type { TradeStatus } from '@prisma/client';
import { StatusBadge, DataTable } from '../../components/ui';
import { formatCurrency, formatNumber } from '../../lib/format';
import { parseTradeQuery } from '../../lib/trade-query';
import { listTrades, type TradeQueryParams } from '../../lib/trade-service';

interface TradesPageProps {
  searchParams?: Record<string, string | string[] | undefined>;
}

const statusOrder: TradeStatus[] = ['NEW', 'ACCEPTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'REJECTED', 'FAILED'];

const normalizeSearchParams = (
  searchParams: TradesPageProps['searchParams'],
): Record<string, string> => {
  if (!searchParams) {
    return {};
  }

  const entries = Object.entries(searchParams).flatMap(([key, value]) => {
    if (Array.isArray(value)) {
      const first = value[0];
      return first ? [[key, first]] : [];
    }
    return value ? [[key, value]] : [];
  });

  return Object.fromEntries(entries);
};

const toNumber = (value: unknown): number => {
  const numeric = Number(value);
  return Number.isNaN(numeric) ? 0 : numeric;
};

const decimalToNumberOrNull = (value: unknown): number | null => {
  if (value === null || value === undefined) {
    return null;
  }

  const numeric = Number(value);
  return Number.isNaN(numeric) ? null : numeric;
};

const buildPageLink = (baseParams: Record<string, string>, page: number) => {
  const params = new URLSearchParams(baseParams);
  params.set('page', String(page));
  return `/trades?${params.toString()}`;
};

export const revalidate = 0;

export default async function TradesPage({ searchParams }: TradesPageProps) {
  const normalizedParams = normalizeSearchParams(searchParams);
  let filters: TradeQueryParams | undefined;
  let validationError: string | null = null;

  try {
    filters = parseTradeQuery(normalizedParams);
  } catch (error) {
    validationError = error instanceof Error ? error.message : 'Invalid filters supplied';
  }

  const result = validationError ? { trades: [], total: 0, page: 1, pageSize: 20 } : await listTrades(filters ?? {});

  const trades = result.trades.map((trade) => ({
    id: trade.id,
    symbol: trade.symbol,
    status: trade.status,
    createdAt: trade.createdAt,
    submittedAt: trade.submittedAt,
    filledAt: trade.filledAt,
    clientOrderId: trade.clientOrderId,
    notionalSubmitted: decimalToNumberOrNull(trade.notionalSubmitted),
    qtySubmitted: decimalToNumberOrNull(trade.qtySubmitted),
    filledQty: decimalToNumberOrNull(trade.filledQty),
    filledAvgPrice: decimalToNumberOrNull(trade.filledAvgPrice),
  }));

  const statusCounts = trades.reduce<Record<string, number>>((acc, trade) => {
    acc[trade.status] = (acc[trade.status] ?? 0) + 1;
    return acc;
  }, {});

  const totalNotional = trades.reduce((sum, trade) => sum + toNumber(trade.notionalSubmitted), 0);
  const filledNotional = trades.reduce((sum, trade) => {
    if (trade.status === 'FILLED' || trade.status === 'PARTIALLY_FILLED') {
      return sum + toNumber(trade.notionalSubmitted);
    }
    return sum;
  }, 0);

  const totalPages = Math.max(1, Math.ceil(result.total / result.pageSize));

  return (
    <section style={{ padding: '2rem 1.5rem', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      <header style={{ marginBottom: '1.5rem' }}>
        <p style={{ color: '#94a3b8', fontSize: '0.8rem', letterSpacing: '0.12em', textTransform: 'uppercase' }}>Trade Log</p>
        <h1 style={{ fontSize: '2rem', margin: '0.25rem 0 0.75rem' }}>Submitted orders</h1>
        <p style={{ color: '#cbd5f5', maxWidth: '720px' }}>
          Filter by ticker symbol or filing date range. Results are served by an internal API route that reuses the shared
          Prisma repositories, ensuring pagination stays consistent with the worker’s writes.
        </p>
      </header>

      <section
        aria-label="Filters"
        style={{
          background: '#111827',
          borderRadius: '0.75rem',
          padding: '1rem 1.5rem',
          border: '1px solid rgba(148, 163, 184, 0.3)',
          marginBottom: '1.5rem',
        }}
      >
        <form method="get" style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', color: '#cbd5f5', fontSize: '0.8rem' }}>
            Ticker
            <input
              type="text"
              name="symbol"
              defaultValue={normalizedParams.symbol ?? ''}
              placeholder="eg. NVDA"
              style={{
                background: '#0f172a',
                border: '1px solid rgba(148, 163, 184, 0.3)',
                borderRadius: '0.5rem',
                padding: '0.65rem 0.75rem',
                color: '#e2e8f0',
                minWidth: '140px',
              }}
            />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', color: '#cbd5f5', fontSize: '0.8rem' }}>
            Start date
            <input
              type="date"
              name="startDate"
              defaultValue={normalizedParams.startDate ?? ''}
              style={{
                background: '#0f172a',
                border: '1px solid rgba(148, 163, 184, 0.3)',
                borderRadius: '0.5rem',
                padding: '0.65rem 0.75rem',
                color: '#e2e8f0',
              }}
            />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', color: '#cbd5f5', fontSize: '0.8rem' }}>
            End date
            <input
              type="date"
              name="endDate"
              defaultValue={normalizedParams.endDate ?? ''}
              style={{
                background: '#0f172a',
                border: '1px solid rgba(148, 163, 184, 0.3)',
                borderRadius: '0.5rem',
                padding: '0.65rem 0.75rem',
                color: '#e2e8f0',
              }}
            />
          </label>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              type="submit"
              style={{
                background: '#38bdf8',
                color: '#0f172a',
                borderRadius: '0.5rem',
                padding: '0.65rem 1.25rem',
                border: 'none',
                fontWeight: 600,
              }}
            >
              Apply
            </button>
            <a
              href="/trades"
              style={{
                background: '#1e293b',
                color: '#e2e8f0',
                borderRadius: '0.5rem',
                padding: '0.65rem 1.25rem',
                border: '1px solid rgba(148, 163, 184, 0.35)',
                textDecoration: 'none',
                fontWeight: 500,
              }}
            >
              Clear
            </a>
          </div>
        </form>

        {validationError ? (
          <p style={{ marginTop: '1rem', color: '#f87171', fontSize: '0.85rem' }}>{validationError}</p>
        ) : null}
      </section>

      <section style={{ marginBottom: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
        <div
          style={{
            background: '#111827',
            borderRadius: '0.75rem',
            padding: '1rem 1.25rem',
            border: '1px solid rgba(148, 163, 184, 0.3)',
            flex: '1 1 220px',
          }}
        >
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Total Notional
          </p>
          <strong style={{ fontSize: '1.35rem' }}>{formatCurrency(totalNotional)}</strong>
        </div>
        <div
          style={{
            background: '#111827',
            borderRadius: '0.75rem',
            padding: '1rem 1.25rem',
            border: '1px solid rgba(148, 163, 184, 0.3)',
            flex: '1 1 220px',
          }}
        >
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Filled Notional
          </p>
          <strong style={{ fontSize: '1.35rem' }}>{formatCurrency(filledNotional)}</strong>
        </div>
        <div
          style={{
            background: '#111827',
            borderRadius: '0.75rem',
            padding: '1rem 1.25rem',
            border: '1px solid rgba(148, 163, 184, 0.3)',
            flex: '1 1 220px',
          }}
        >
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Totals by Status
          </p>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.35rem' }}>
            {statusOrder.map((status) =>
              statusCounts[status] ? (
                <StatusBadge key={status} status={status}>
                  {statusCounts[status]}
                </StatusBadge>
              ) : null,
            )}
            {Object.keys(statusCounts).length === 0 ? (
              <StatusBadge status="EMPTY">0</StatusBadge>
            ) : null}
          </div>
        </div>
      </section>

      <DataTable
        caption="Trades recorded in Postgres"
        columns={[
          {
            key: 'symbol',
            header: 'Symbol',
            accessor: (trade: (typeof trades)[number]) => (
              <strong>{trade.symbol}</strong>
            ),
          },
          {
            key: 'status',
            header: 'Status',
            render: (trade) => <StatusBadge status={trade.status} />,
          },
          {
            key: 'notional',
            header: 'Notional',
            accessor: (trade) => formatCurrency(trade.notionalSubmitted ?? 0),
            align: 'right',
          },
          {
            key: 'qty',
            header: 'Qty Submitted',
            accessor: (trade) => formatNumber(trade.qtySubmitted ?? 0),
            align: 'right',
          },
          {
            key: 'filledQty',
            header: 'Filled Qty',
            accessor: (trade) => formatNumber(trade.filledQty ?? 0),
            align: 'right',
          },
          {
            key: 'filledAvgPrice',
            header: 'Fill Avg',
            accessor: (trade) => formatCurrency(trade.filledAvgPrice ?? 0),
            align: 'right',
          },
          {
            key: 'submittedAt',
            header: 'Submitted',
            accessor: (trade) => (trade.submittedAt ? new Date(trade.submittedAt).toLocaleString() : '—'),
          },
          {
            key: 'filledAt',
            header: 'Filled',
            accessor: (trade) => (trade.filledAt ? new Date(trade.filledAt).toLocaleString() : '—'),
          },
        ]}
        data={trades}
        emptyState={<p style={{ margin: 0, color: '#94a3b8' }}>No trades match the selected filters yet.</p>}
      />

      <nav
        aria-label="Pagination"
        style={{
          marginTop: '1.5rem',
          display: 'flex',
          gap: '0.75rem',
          alignItems: 'center',
          justifyContent: 'flex-end',
          color: '#94a3b8',
        }}
      >
        <span>
          Page {result.page} of {totalPages}
        </span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {result.page > 1 ? (
            <Link
              href={buildPageLink(normalizedParams, result.page - 1)}
              style={{
                padding: '0.5rem 0.85rem',
                borderRadius: '0.5rem',
                background: '#1e293b',
                color: '#e2e8f0',
                textDecoration: 'none',
              }}
            >
              Previous
            </Link>
          ) : null}
          {result.page < totalPages ? (
            <Link
              href={buildPageLink(normalizedParams, result.page + 1)}
              style={{
                padding: '0.5rem 0.85rem',
                borderRadius: '0.5rem',
                background: '#1e293b',
                color: '#e2e8f0',
                textDecoration: 'none',
              }}
            >
              Next
            </Link>
          ) : null}
        </div>
      </nav>
    </section>
  );
}
