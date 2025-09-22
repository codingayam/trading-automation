import type { ReactNode } from 'react';

export type ColumnAlignment = 'left' | 'center' | 'right';

export interface DataTableColumn<Row> {
  key: string;
  header: ReactNode;
  render?: (row: Row, index: number) => ReactNode;
  accessor?: (row: Row) => ReactNode;
  align?: ColumnAlignment;
  width?: string | number;
}

export interface DataTableProps<Row> {
  columns: ReadonlyArray<DataTableColumn<Row>>;
  data: ReadonlyArray<Row>;
  caption?: ReactNode;
  emptyState?: ReactNode;
  footer?: ReactNode;
  dense?: boolean;
  getRowKey?: (row: Row, index: number) => string;
}

const alignmentToTextAlign: Record<ColumnAlignment, 'left' | 'center' | 'right'> = {
  left: 'left',
  center: 'center',
  right: 'right',
};

const baseCellStyle: React.CSSProperties = {
  padding: '0.75rem 1rem',
  borderBottom: '1px solid rgba(148, 163, 184, 0.2)',
  fontSize: '0.875rem',
  color: '#e2e8f0',
};

export function DataTable<Row>({
  columns,
  data,
  caption,
  emptyState,
  footer,
  dense = false,
  getRowKey,
}: DataTableProps<Row>) {
  const cellPadding = dense ? '0.5rem 0.75rem' : baseCellStyle.padding;

  if (!data.length) {
    return (
      <div
        role="status"
        aria-live="polite"
        style={{
          background: '#111827',
          borderRadius: '0.75rem',
          border: '1px solid rgba(148, 163, 184, 0.35)',
          padding: '1.5rem',
        }}
      >
        {emptyState ?? (
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.9rem' }}>No records found for the selected filters.</p>
        )}
      </div>
    );
  }

  return (
    <div
      role="region"
      aria-live="polite"
      style={{
        overflowX: 'auto',
        background: '#111827',
        borderRadius: '0.75rem',
        border: '1px solid rgba(148, 163, 184, 0.35)',
      }}
    >
      <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
        {caption ? (
          <caption
            style={{
              captionSide: 'top',
              textAlign: 'left',
              padding: '1rem',
              color: '#cbd5f5',
              fontSize: '0.9rem',
            }}
          >
            {caption}
          </caption>
        ) : null}

        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                style={{
                  ...baseCellStyle,
                  padding: cellPadding,
                  textAlign: alignmentToTextAlign[column.align ?? 'left'],
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#94a3b8',
                  borderBottom: '1px solid rgba(148, 163, 184, 0.35)',
                  width: column.width,
                }}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {data.map((row, index) => (
            <tr key={getRowKey ? getRowKey(row, index) : index}>
              {columns.map((column) => (
                <td
                  key={column.key}
                  style={{
                    ...baseCellStyle,
                    padding: cellPadding,
                    textAlign: alignmentToTextAlign[column.align ?? 'left'],
                  }}
                >
                  {column.render ? column.render(row, index) : column.accessor ? column.accessor(row) : null}
                </td>
              ))}
            </tr>
          ))}
        </tbody>

        {footer ? (
          <tfoot>
            <tr>
              <td colSpan={columns.length} style={{ ...baseCellStyle, padding: cellPadding }}>{footer}</td>
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}
