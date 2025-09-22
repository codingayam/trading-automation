'use client';

import type { PositionBreakdownEntry } from '../../lib/overview-service';
import { formatCurrency } from '../../lib/format';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export interface PortfolioDistributionChartProps {
  data: PositionBreakdownEntry[];
}

const formatCompactCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value);

const colors = {
  marketValue: '#38bdf8',
  costBasis: '#f97316',
  unrealizedPl: '#22c55e',
};

export function PortfolioDistributionChart({ data }: PortfolioDistributionChartProps) {
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.25)" />
          <XAxis dataKey="symbol" stroke="#cbd5f5" fontSize={12} />
          <YAxis tickFormatter={formatCompactCurrency} stroke="#cbd5f5" fontSize={12} />
          <Legend wrapperStyle={{ color: '#cbd5f5' }} />
          <Tooltip
            cursor={{ fill: 'rgba(148, 163, 184, 0.15)' }}
            contentStyle={{
              backgroundColor: '#0f172a',
              borderRadius: '0.5rem',
              border: '1px solid rgba(148, 163, 184, 0.3)',
              color: '#e2e8f0',
            }}
            formatter={(value: number, name) => [formatCurrency(value), name]}
          />
          <Bar dataKey="marketValue" name="Market Value" fill={colors.marketValue} radius={[4, 4, 0, 0]} />
          <Bar dataKey="costBasis" name="Cost Basis" fill={colors.costBasis} radius={[4, 4, 0, 0]} />
          <Bar dataKey="unrealizedPl" name="Unrealized P/L" fill={colors.unrealizedPl} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
