import type {
  Prisma,
  PrismaClient,
  Trade,
  TradeStatus,
  TradeSide,
  TradeOrderType,
  TradeTimeInForce,
} from '@prisma/client';
import { Prisma as PrismaNamespace } from '@prisma/client';
import { resolveClient, type TransactionClient } from '../transactions';
import { rethrowKnownPrismaErrors } from '../prisma-errors';

type DecimalInput = PrismaNamespace.Decimal | number | string | null | undefined;

const toDecimal = (value: DecimalInput): PrismaNamespace.Decimal | undefined => {
  if (value === null || value === undefined || value === '') {
    return undefined;
  }

  if (value instanceof PrismaNamespace.Decimal) {
    return value;
  }

  return new PrismaNamespace.Decimal(value);
};

export interface CreateTradeAttemptParams {
  sourceHash: string;
  symbol: string;
  side?: TradeSide;
  orderType?: TradeOrderType;
  timeInForce?: TradeTimeInForce;
  status?: TradeStatus;
  notionalSubmitted?: DecimalInput;
  qtySubmitted?: DecimalInput;
  congressTradeFeedId?: string;
  clientOrderId?: string | null;
  alpacaOrderId?: string | null;
  submittedAt?: Date | null;
  rawOrderJson?: Prisma.InputJsonValue | null;
}

export interface UpdateTradeParams {
  id: string;
  status?: TradeStatus;
  clientOrderId?: string | null;
  alpacaOrderId?: string | null;
  submittedAt?: Date | null;
  filledQty?: DecimalInput;
  filledAvgPrice?: DecimalInput;
  filledAt?: Date | null;
  canceledAt?: Date | null;
  failedAt?: Date | null;
  notionalSubmitted?: DecimalInput;
  qtySubmitted?: DecimalInput;
  rawOrderJson?: Prisma.InputJsonValue | null;
}

export interface UpsertTradeParams {
  sourceHash: string;
  create: CreateTradeAttemptParams;
  update: UpdateTradeParams;
  tx?: TransactionClient;
}

export interface ListOpenTradesParams {
  statuses?: TradeStatus[];
  limit?: number;
  tx?: TransactionClient;
}

export class TradeRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async createTradeAttempt(params: CreateTradeAttemptParams, tx?: TransactionClient): Promise<Trade> {
    const client = resolveClient(this.prisma, tx);

    const {
      sourceHash,
      symbol,
      side,
      orderType,
      timeInForce,
      status,
      notionalSubmitted,
      qtySubmitted,
      congressTradeFeedId,
      clientOrderId,
      alpacaOrderId,
      submittedAt,
      rawOrderJson,
    } = params;

    try {
      return await client.trade.create({
        data: {
          sourceHash,
          symbol,
          side: side ?? 'BUY',
          orderType: orderType ?? 'MARKET',
          timeInForce: timeInForce ?? 'DAY',
          status: status ?? 'NEW',
          notionalSubmitted: toDecimal(notionalSubmitted),
          qtySubmitted: toDecimal(qtySubmitted),
          congressTradeFeed: congressTradeFeedId
            ? {
                connect: { id: congressTradeFeedId },
              }
            : undefined,
          clientOrderId: clientOrderId ?? undefined,
          alpacaOrderId: alpacaOrderId ?? undefined,
          submittedAt: submittedAt ?? undefined,
          rawOrderJson: rawOrderJson ?? undefined,
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate trade detected');
    }
  }

  async upsertBySourceHash(params: UpsertTradeParams): Promise<Trade> {
    const client = resolveClient(this.prisma, params.tx);

    try {
      return await client.trade.upsert({
        where: { sourceHash: params.sourceHash },
        create: this.buildCreateData(params.create),
        update: this.buildUpdateData(params.update),
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate trade detected');
    }
  }

  async updateTrade(params: UpdateTradeParams, tx?: TransactionClient): Promise<Trade> {
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.trade.update({
        where: { id: params.id },
        data: this.buildUpdateData(params),
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate trade detected');
    }
  }

  async findBySourceHash(sourceHash: string, tx?: TransactionClient): Promise<Trade | null> {
    const client = resolveClient(this.prisma, tx);
    return client.trade.findUnique({ where: { sourceHash } });
  }

  async findByAlpacaOrderId(alpacaOrderId: string, tx?: TransactionClient): Promise<Trade | null> {
    const client = resolveClient(this.prisma, tx);
    return client.trade.findUnique({ where: { alpacaOrderId } });
  }

  async listOpenTrades(params: ListOpenTradesParams = {}): Promise<Trade[]> {
    const { statuses = ['NEW', 'ACCEPTED', 'PARTIALLY_FILLED'], limit, tx } = params;
    const client = resolveClient(this.prisma, tx);

    return client.trade.findMany({
      where: {
        status: {
          in: statuses,
        },
      },
      orderBy: { createdAt: 'asc' },
      take: limit,
    });
  }

  async attachCongressTradeFeed(tradeId: string, feedId: string, tx?: TransactionClient): Promise<Trade> {
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.trade.update({
        where: { id: tradeId },
        data: {
          congressTradeFeed: {
            connect: { id: feedId },
          },
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate trade detected');
    }
  }

  private buildCreateData(params: CreateTradeAttemptParams): Prisma.TradeCreateInput {
    const {
      sourceHash,
      symbol,
      side,
      orderType,
      timeInForce,
      status,
      notionalSubmitted,
      qtySubmitted,
      congressTradeFeedId,
      clientOrderId,
      alpacaOrderId,
      submittedAt,
      rawOrderJson,
    } = params;

    return {
      sourceHash,
      symbol,
      side: side ?? 'BUY',
      orderType: orderType ?? 'MARKET',
      timeInForce: timeInForce ?? 'DAY',
      status: status ?? 'NEW',
      notionalSubmitted: toDecimal(notionalSubmitted),
      qtySubmitted: toDecimal(qtySubmitted),
      congressTradeFeed: congressTradeFeedId
        ? {
            connect: { id: congressTradeFeedId },
          }
        : undefined,
      clientOrderId: clientOrderId ?? undefined,
      alpacaOrderId: alpacaOrderId ?? undefined,
      submittedAt: submittedAt ?? undefined,
      rawOrderJson: rawOrderJson ?? undefined,
    };
  }

  private buildUpdateData(params: UpdateTradeParams): Prisma.TradeUpdateInput {
    const {
      status,
      clientOrderId,
      alpacaOrderId,
      submittedAt,
      filledQty,
      filledAvgPrice,
      filledAt,
      canceledAt,
      failedAt,
      notionalSubmitted,
      qtySubmitted,
      rawOrderJson,
    } = params;

    return {
      status,
      clientOrderId,
      alpacaOrderId,
      submittedAt,
      filledQty: toDecimal(filledQty),
      filledAvgPrice: toDecimal(filledAvgPrice),
      filledAt,
      canceledAt,
      failedAt,
      notionalSubmitted: toDecimal(notionalSubmitted),
      qtySubmitted: toDecimal(qtySubmitted),
      rawOrderJson,
    };
  }
}

export const createTradeRepository = (prisma: PrismaClient): TradeRepository => new TradeRepository(prisma);
