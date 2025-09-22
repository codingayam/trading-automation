import { z } from 'zod';
import type { TradeQueryParams } from './trade-service';

const isoDate = z
  .string()
  .trim()
  .regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format')
  .transform((value) => new Date(`${value}T00:00:00.000Z`));

const tradeQuerySchema = z
  .object({
    page: z.coerce.number().int().positive().optional(),
    pageSize: z.coerce.number().int().positive().max(100).optional(),
    symbol: z
      .string()
      .trim()
      .max(12, 'Ticker symbol too long')
      .transform((value) => value.toUpperCase())
      .optional(),
    startDate: isoDate.optional(),
    endDate: isoDate.optional(),
  })
  .superRefine((value, ctx) => {
    if (value.startDate && value.endDate && value.startDate > value.endDate) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'startDate must be before endDate',
        path: ['startDate'],
      });
    }
  });

export type TradeQuery = z.infer<typeof tradeQuerySchema>;

const toEndOfDay = (date: Date | undefined): Date | undefined => {
  if (!date) {
    return undefined;
  }

  const end = new Date(date.getTime());
  end.setUTCHours(23, 59, 59, 999);
  return end;
};

export const parseTradeQuery = (params: URLSearchParams | Record<string, unknown>): TradeQueryParams => {
  const raw = params instanceof URLSearchParams ? Object.fromEntries(params.entries()) : params;

  const parsed = tradeQuerySchema.safeParse(raw);

  if (!parsed.success) {
    const message = parsed.error.issues.map((issue) => issue.message).join(', ');
    throw new Error(message || 'Invalid query parameters');
  }

  return {
    page: parsed.data.page,
    pageSize: parsed.data.pageSize,
    symbol: parsed.data.symbol,
    startDate: parsed.data.startDate,
    endDate: toEndOfDay(parsed.data.endDate),
  } satisfies TradeQueryParams;
};
