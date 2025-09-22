import type { ReactNode } from 'react';

export interface MetricCardProps {
  title: string;
  value: ReactNode;
  subtitle?: ReactNode;
  description?: ReactNode;
  accent?: 'primary' | 'neutral' | 'success' | 'warning' | 'danger';
  footer?: ReactNode;
}

const ACCENT_STYLES: Record<NonNullable<MetricCardProps['accent']>, { border: string; text: string }> = {
  primary: { border: '#38bdf8', text: '#e0f2fe' },
  neutral: { border: '#334155', text: '#e2e8f0' },
  success: { border: '#22c55e', text: '#dcfce7' },
  warning: { border: '#facc15', text: '#fef9c3' },
  danger: { border: '#f87171', text: '#fee2e2' },
};

export function MetricCard({ title, value, subtitle, description, footer, accent = 'neutral' }: MetricCardProps) {
  const accentStyle = ACCENT_STYLES[accent];

  return (
    <article
      aria-label={typeof title === 'string' ? title : undefined}
      style={{
        background: '#111827',
        borderRadius: '0.75rem',
        padding: '1.25rem',
        border: `1px solid ${accentStyle.border}`,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        minHeight: '160px',
      }}
    >
      <header>
        <p style={{ margin: 0, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#94a3b8' }}>
          {title}
        </p>
        {subtitle ? (
          <p style={{ margin: '0.25rem 0 0', color: '#cbd5f5', fontSize: '0.85rem' }}>{subtitle}</p>
        ) : null}
      </header>

      <div style={{ fontSize: '2rem', fontWeight: 600, color: accentStyle.text }}>{value}</div>

      {description ? (
        <p style={{ margin: 0, fontSize: '0.875rem', color: '#cbd5f5', flexGrow: 1 }}>{description}</p>
      ) : (
        <div style={{ flexGrow: 1 }} />
      )}

      {footer ? (
        <footer style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{footer}</footer>
      ) : null}
    </article>
  );
}
