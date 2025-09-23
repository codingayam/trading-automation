import type { JobRun, JobRunStatus, JobRunType, Prisma, PrismaClient } from '@prisma/client';
import { resolveClient, type TransactionClient } from '../transactions.js';
import { rethrowKnownPrismaErrors } from '../prisma-errors.js';

export interface StartJobRunParams {
  tradingDateEt: Date;
  type?: JobRunType;
  summaryJson?: Prisma.InputJsonValue | null;
  tx?: TransactionClient;
}

export interface CompleteJobRunParams {
  tradingDateEt: Date;
  type?: JobRunType;
  summaryJson?: Prisma.InputJsonValue | null;
  finishedAt?: Date;
  tx?: TransactionClient;
}

export interface FailJobRunParams extends CompleteJobRunParams {}

export class JobRunRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async getByTradingDate(
    tradingDateEt: Date,
    type: JobRunType = 'OPEN_JOB',
    tx?: TransactionClient,
  ): Promise<JobRun | null> {
    const client = resolveClient(this.prisma, tx);
    return client.jobRun.findUnique({
      where: {
        type_tradingDateEt: {
          type,
          tradingDateEt,
        },
      },
    });
  }

  async start(params: StartJobRunParams): Promise<JobRun> {
    const { tradingDateEt, type = 'OPEN_JOB', summaryJson, tx } = params;
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.jobRun.upsert({
        where: {
          type_tradingDateEt: {
            type,
            tradingDateEt,
          },
        },
        update: {
          status: 'RUNNING',
          startedAt: new Date(),
          summaryJson: summaryJson ?? undefined,
        },
        create: {
          type,
          tradingDateEt,
          status: 'RUNNING',
          startedAt: new Date(),
          summaryJson: summaryJson ?? undefined,
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate job run entry detected');
      throw error;
    }
  }

  async complete(params: CompleteJobRunParams): Promise<JobRun> {
    const { tradingDateEt, type = 'OPEN_JOB', summaryJson, finishedAt = new Date(), tx } = params;
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.jobRun.update({
        where: {
          type_tradingDateEt: {
            type,
            tradingDateEt,
          },
        },
        data: {
          status: 'SUCCESS',
          finishedAt,
          summaryJson: summaryJson ?? undefined,
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate job run entry detected');
      throw error;
    }
  }

  async fail(params: FailJobRunParams): Promise<JobRun> {
    const { tradingDateEt, type = 'OPEN_JOB', summaryJson, finishedAt = new Date(), tx } = params;
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.jobRun.update({
        where: {
          type_tradingDateEt: {
            type,
            tradingDateEt,
          },
        },
        data: {
          status: 'FAILED',
          finishedAt,
          summaryJson: summaryJson ?? undefined,
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate job run entry detected');
      throw error;
    }
  }

  async updateSummary(
    tradingDateEt: Date,
    summaryJson: Prisma.InputJsonValue,
    type: JobRunType = 'OPEN_JOB',
    tx?: TransactionClient,
  ): Promise<JobRun> {
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.jobRun.update({
        where: {
          type_tradingDateEt: {
            type,
            tradingDateEt,
          },
        },
        data: {
          summaryJson,
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate job run entry detected');
      throw error;
    }
  }

  async listRecent(limit = 10, type: JobRunType = 'OPEN_JOB', tx?: TransactionClient): Promise<JobRun[]> {
    const client = resolveClient(this.prisma, tx);

    return client.jobRun.findMany({
      where: { type },
      orderBy: { tradingDateEt: 'desc' },
      take: limit,
    });
  }

  async markStatus(
    tradingDateEt: Date,
    status: JobRunStatus,
    options: { summaryJson?: Prisma.InputJsonValue | null; timestamp?: Date; type?: JobRunType; tx?: TransactionClient } = {},
  ): Promise<JobRun> {
    const { summaryJson, timestamp = new Date(), type = 'OPEN_JOB', tx } = options;
    const client = resolveClient(this.prisma, tx);

    try {
      return await client.jobRun.update({
        where: {
          type_tradingDateEt: {
            type,
            tradingDateEt,
          },
        },
        data: {
          status,
          finishedAt: ['SUCCESS', 'FAILED'].includes(status) ? timestamp : undefined,
          summaryJson: summaryJson ?? undefined,
        },
      });
    } catch (error) {
      rethrowKnownPrismaErrors(error, 'Duplicate job run entry detected');
      throw error;
    }
  }
}

export const createJobRunRepository = (prisma: PrismaClient): JobRunRepository => new JobRunRepository(prisma);
