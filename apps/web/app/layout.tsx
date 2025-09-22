import type { ReactNode } from 'react';

export const metadata = {
  title: 'Congress Mirror Dashboard',
  description: 'Monitor automated congressional trading activity and worker status.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, sans-serif', margin: 0, background: '#0f172a', color: '#f8fafc' }}>
        {children}
      </body>
    </html>
  );
}
