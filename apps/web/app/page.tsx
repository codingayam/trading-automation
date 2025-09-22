import { loadWebEnv } from '@trading-automation/shared';

const cards: Array<{ title: string; body: string }> = [
  {
    title: 'Worker Service',
    body: 'Railway invokes `pnpm run open-job` at 13:30/14:30 UTC. The worker validates env vars and emits structured logs via Pino.',
  },
  {
    title: 'Dashboard Refresh',
    body: 'Data fetches should opt into Next.js caching. Default `NEXT_PUBLIC_REVALIDATE_SECONDS` is set to 60 for Alpaca-derived views.',
  },
  {
    title: 'Shared Toolkit',
    body: 'Services share env parsing, HTTP retry helpers, and logging through `@trading-automation/shared` to keep behaviour consistent.',
  },
];

export default function HomePage() {
  const env = loadWebEnv();

  return (
    <main style={{ minHeight: '100vh', padding: '3rem 1.5rem', maxWidth: '960px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2.5rem' }}>
        <p style={{ textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.75rem', color: '#94a3b8' }}>
          Congress Mirror
        </p>
        <h1 style={{ fontSize: '2.75rem', margin: '0.5rem 0' }}>Trading Automation Dashboard</h1>
        <p style={{ maxWidth: '640px', color: '#cbd5f5' }}>
          Starter shell for the UI team. Hook Prisma queries, Alpaca polling, and Quiver status indicators here without touching
          the workspace plumbing delivered by Group 01.
        </p>
        <pre
          style={{
            background: '#1e293b',
            borderRadius: '0.5rem',
            padding: '1rem',
            color: '#e2e8f0',
            overflowX: 'auto',
            fontSize: '0.875rem',
          }}
        >
{`# Run both services locally
pnpm install
pnpm dev        # Next.js (apps/web)
pnpm open-job   # Worker no-op entrypoint`}
        </pre>
      </header>

      <section style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
        {cards.map((card) => (
          <article key={card.title} style={{ background: '#1e293b', borderRadius: '0.75rem', padding: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', marginTop: 0 }}>{card.title}</h2>
            <p style={{ color: '#cbd5f5', marginBottom: 0 }}>{card.body}</p>
          </article>
        ))}
      </section>

      <footer style={{ marginTop: '3rem', color: '#94a3b8', fontSize: '0.875rem' }}>
        <p>
          Environment: <strong>{env.NODE_ENV}</strong> · Default revalidate: <strong>{env.NEXT_PUBLIC_REVALIDATE_SECONDS}s</strong>
        </p>
        <p style={{ color: '#cbd5f5' }}>
          Reference <code>docs/development-workflow.md</code> for concurrent run instructions and Railway integration notes.
        </p>
      </footer>
    </main>
  );
}
