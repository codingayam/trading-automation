import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricCard, StatusBadge, DataTable } from '../index';

const sampleRows = [
  { id: '1', name: 'Sample', value: 42 },
  { id: '2', name: 'Another', value: 7 },
];

describe('UI component library', () => {
  it('renders metric card with title, value, and description', () => {
    render(<MetricCard title="Portfolio Value" value="$10,000" description="Includes open positions" />);

    expect(screen.getByText('Portfolio Value')).toBeInTheDocument();
    expect(screen.getByText('$10,000')).toBeInTheDocument();
    expect(screen.getByText('Includes open positions')).toBeInTheDocument();
  });

  it('renders status badge with default label and extra content', () => {
    render(<StatusBadge status="FILLED">2</StatusBadge>);

    expect(screen.getByText('Filled')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders data table rows and headers', () => {
    render(
      <DataTable
        columns={[
          { key: 'name', header: 'Name', accessor: (row: (typeof sampleRows)[number]) => row.name },
          { key: 'value', header: 'Value', accessor: (row) => row.value },
        ]}
        data={sampleRows}
        caption="Sample table"
      />,
    );

    expect(screen.getByText('Sample table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Value' })).toBeInTheDocument();
    expect(screen.getByText('Sample')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders empty state when no data is provided', () => {
    render(
      <DataTable
        columns={[{ key: 'name', header: 'Name', accessor: () => 'unused' }]}
        data={[]}
        emptyState={<p>No rows</p>}
      />,
    );

    expect(screen.getByText('No rows')).toBeInTheDocument();
  });
});
