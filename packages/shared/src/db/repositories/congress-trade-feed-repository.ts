import type {
  CongressTradeFeed,
  CongressTradeTransaction,
  CongressParty,
  Prisma,
  PrismaClient,
} from '@prisma/client';
import { resolveClient, type TransactionClient } from '../transactions';
import { rethrowKnownPrismaErrors } from '../prisma-errors';

export interface CreateFeedEntryParams {
  ticker: string;
  memberName: string;
  transaction: CongressTradeTransaction;
  tradeDate: Date;
  filingDate: Date;
  party?: CongressParty | null;
  rawJson: Prisma.InputJsonValue;
  ingestedAt?: Date;
  tx?: TransactionClient;
}

export interface ListFeedParams {
  since?: Date;
  ticker?: string;
  limit?: number;
  tx?: TransactionClient;
}

export class CongressTradeFeedRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async create(params: CreateFeedEntryParams): Promise<CongressTradeFeed> {
    const { tx, ...data } = params;
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.congressTradeFeed.create({
        data: {
          ...data,
          ingestedAt: data.ingestedAt ?? new Date(),
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate trade feed entry detected');
    }
  }

  async createMany(entries: CreateFeedEntryParams[], tx?: TransactionClient): Promise<void> {
    if (!entries.length) {
      return;
    }

    const client = resolveClient(this.prisma, tx);
    try {
      await client.congressTradeFeed.createMany({
        data: entries.map(({ tx: _tx, ingestedAt, ...entry }) => ({
          ...entry,
          ingestedAt: ingestedAt ?? new Date(),
        })),
        skipDuplicates: true,
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate trade feed entry detected');
    }
  }

  async list(params: ListFeedParams = {}): Promise<CongressTradeFeed[]> {
    const { since, ticker, limit = 100, tx } = params;
    const client = resolveClient(this.prisma, tx);

    return client.congressTradeFeed.findMany({
      where: {
        AND: [
          since
            ? {
                filingDate: {
                  gte: since,
                },
              }
            : {},
          ticker ? { ticker } : {},
        ],
      },
      orderBy: { filingDate: 'desc' },
      take: limit,
    });
  }

  async findLatestFilingDate(tx?: TransactionClient): Promise<Date | null> {
    const client = resolveClient(this.prisma, tx);
    const latest = await client.congressTradeFeed.findFirst({
      orderBy: { filingDate: 'desc' },
      select: { filingDate: true },
    });

    return latest?.filingDate ?? null;
  }
}

export const createCongressTradeFeedRepository = (prisma: PrismaClient): CongressTradeFeedRepository =>
  new CongressTradeFeedRepository(prisma);
