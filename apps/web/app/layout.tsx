import type { ReactNode } from 'react';

export const metadata = {
  title: 'Congress Mirror Dashboard',
  description: 'Monitor automated congressional trading activity and worker status.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily: 'system-ui, sans-serif',
          margin: 0,
          background: '#0f172a',
          color: '#f8fafc',
        }}
      >
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
          <header
            style={{
              borderBottom: '1px solid rgba(148, 163, 184, 0.25)',
              background: 'rgba(15, 23, 42, 0.95)',
              backdropFilter: 'blur(6px)',
            }}
          >
            <div
              style={{
                maxWidth: '1200px',
                margin: '0 auto',
                padding: '1rem 1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
              }}
            >
              <a
                href="/"
                style={{
                  display: 'inline-flex',
                  flexDirection: 'column',
                  gap: '0.15rem',
                  textDecoration: 'none',
                  color: '#e2e8f0',
                }}
              >
                <strong style={{ fontSize: '1.1rem' }}>Congress Mirror</strong>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', letterSpacing: '0.1em' }}>AUTOMATED TRADING</span>
              </a>

              <nav style={{ display: 'flex', gap: '1rem', alignItems: 'center' }} aria-label="Primary">
                {[
                  { href: '/overview', label: 'Overview' },
                  { href: '/trades', label: 'Trades' },
                  { href: '/positions', label: 'Positions' },
                ].map((item) => (
                  <a
                    key={item.href}
                    href={item.href}
                    style={{
                      color: '#cbd5f5',
                      textDecoration: 'none',
                      fontSize: '0.9rem',
                      fontWeight: 500,
                    }}
                  >
                    {item.label}
                  </a>
                ))}
              </nav>
            </div>
          </header>

          <main style={{ flex: 1 }}>{children}</main>

          <footer style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.75rem' }}>
            <span>Congress Mirror · Alpaca Paper Trading · {new Date().getFullYear()}</span>
          </footer>
        </div>
      </body>
    </html>
  );
}
