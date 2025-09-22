import type { TradeStatus } from '@prisma/client';
import type { ReactNode } from 'react';

export interface StatusBadgeProps {
  status: TradeStatus | 'PENDING' | 'ERROR' | 'EMPTY';
  children?: ReactNode;
}

const STATUS_CONFIG: Record<string, { label: string; background: string; color: string }> = {
  NEW: { label: 'New', background: '#1d4ed8', color: '#dbeafe' },
  ACCEPTED: { label: 'Accepted', background: '#0f766e', color: '#ccfbf1' },
  PARTIALLY_FILLED: { label: 'Partially Filled', background: '#ca8a04', color: '#fef08a' },
  FILLED: { label: 'Filled', background: '#166534', color: '#dcfce7' },
  CANCELED: { label: 'Canceled', background: '#7f1d1d', color: '#fee2e2' },
  REJECTED: { label: 'Rejected', background: '#831843', color: '#fbcfe8' },
  FAILED: { label: 'Failed', background: '#7f1d1d', color: '#fee2e2' },
  PENDING: { label: 'Pending', background: '#1e293b', color: '#cbd5f5' },
  ERROR: { label: 'Error', background: '#991b1b', color: '#fecaca' },
  EMPTY: { label: 'No Data', background: '#334155', color: '#e2e8f0' },
};

export function StatusBadge({ status, children }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.ERROR;

  return (
    <span
      aria-label={config.label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.35rem',
        padding: '0.25rem 0.6rem',
        borderRadius: '999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        background: config.background,
        color: config.color,
        letterSpacing: '0.02em',
      }}
    >
      <span>{config.label}</span>
      {children ? <span style={{ color: '#e2e8f0', fontWeight: 500 }}>{children}</span> : null}
    </span>
  );
}
