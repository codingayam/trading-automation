const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
});

const percentFormatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
});

export const formatCurrency = (value: number | string | null | undefined): string => {
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (numeric === null || numeric === undefined || Number.isNaN(numeric)) {
    return '$0.00';
  }
  return currencyFormatter.format(numeric);
};

export const formatPercent = (value: number | string | null | undefined): string => {
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (numeric === null || numeric === undefined || Number.isNaN(numeric)) {
    return '0.00%';
  }
  return percentFormatter.format(numeric);
};

export const formatNumber = (value: number | string | null | undefined): string => {
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (numeric === null || numeric === undefined || Number.isNaN(numeric)) {
    return '0';
  }
  return numberFormatter.format(numeric);
};
