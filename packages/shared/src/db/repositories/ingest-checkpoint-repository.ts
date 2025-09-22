import type { IngestCheckpoint, PrismaClient } from '@prisma/client';
import { resolveClient, type TransactionClient } from '../transactions';
import { rethrowKnownPrismaErrors } from '../prisma-errors';

export interface UpsertCheckpointParams {
  tradingDateEt: Date;
  lastFiledTsProcessedEt: Date | null;
  tx?: TransactionClient;
}

export class IngestCheckpointRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async get(tradingDateEt: Date, tx?: TransactionClient): Promise<IngestCheckpoint | null> {
    const client = resolveClient(this.prisma, tx);
    return client.ingestCheckpoint.findUnique({ where: { tradingDateEt } });
  }

  async upsert(params: UpsertCheckpointParams): Promise<IngestCheckpoint> {
    const { tradingDateEt, lastFiledTsProcessedEt, tx } = params;
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.ingestCheckpoint.upsert({
        where: { tradingDateEt },
        update: {
          lastFiledTsProcessedEt,
        },
        create: {
          tradingDateEt,
          lastFiledTsProcessedEt,
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate ingest checkpoint detected');
    }
  }

  async delete(tradingDateEt: Date, tx?: TransactionClient): Promise<IngestCheckpoint> {
    const client = resolveClient(this.prisma, tx);
    try {
      return await client.ingestCheckpoint.delete({ where: { tradingDateEt } });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate ingest checkpoint detected');
    }
  }

  async list(limit = 30, tx?: TransactionClient): Promise<IngestCheckpoint[]> {
    const client = resolveClient(this.prisma, tx);
    return client.ingestCheckpoint.findMany({ orderBy: { tradingDateEt: 'desc' }, take: limit });
  }
}

export const createIngestCheckpointRepository = (prisma: PrismaClient): IngestCheckpointRepository =>
  new IngestCheckpointRepository(prisma);
