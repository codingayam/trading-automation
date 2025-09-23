import type { Prisma, TradeStatus } from '@prisma/client';
import type { AlpacaOrder, AlpacaOrderStatus } from './types.js';

const STATUS_MAP: Record<AlpacaOrderStatus, TradeStatus> = {
  new: 'NEW',
  accepted: 'ACCEPTED',
  partially_filled: 'PARTIALLY_FILLED',
  filled: 'FILLED',
  canceled: 'CANCELED',
  pending_new: 'ACCEPTED',
  pending_cancel: 'CANCELED',
  rejected: 'REJECTED',
  expired: 'CANCELED',
  stopped: 'CANCELED',
  suspended: 'FAILED',
  calculated: 'FAILED',
};

const TERMINAL_STATUSES: ReadonlySet<TradeStatus> = new Set(['FILLED', 'CANCELED', 'REJECTED', 'FAILED']);

const toDate = (timestamp: string | null | undefined): Date | undefined => {
  if (!timestamp) {
    return undefined;
  }

  const parsed = new Date(timestamp);

  return Number.isNaN(parsed.getTime()) ? undefined : parsed;
};

export const mapAlpacaStatusToTradeStatus = (status: AlpacaOrderStatus): TradeStatus =>
  STATUS_MAP[status] ?? 'FAILED';

export const isTerminalTradeStatus = (status: TradeStatus): boolean => TERMINAL_STATUSES.has(status);

const toJsonObject = (order: AlpacaOrder): Prisma.InputJsonValue => order as unknown as Prisma.JsonObject;

export const buildTradeUpdateFromOrder = (order: AlpacaOrder) => ({
  status: mapAlpacaStatusToTradeStatus(order.status),
  clientOrderId: order.client_order_id,
  alpacaOrderId: order.id,
  submittedAt: toDate(order.submitted_at ?? undefined),
  filledQty: order.filled_qty,
  filledAvgPrice: order.filled_avg_price,
  filledAt: toDate(order.filled_at ?? undefined),
  canceledAt: toDate(order.canceled_at ?? undefined),
  failedAt: toDate(order.failed_at ?? undefined),
  rawOrderJson: toJsonObject(order),
});
