import type { PrismaClient, Prisma } from '@prisma/client';

export type TransactionClient = Prisma.TransactionClient;

export interface TransactionOptions extends Prisma.TransactionOptions {}

export const runInTransaction = async <T>(
  client: PrismaClient,
  handler: (tx: TransactionClient) => Promise<T>,
  options?: TransactionOptions,
): Promise<T> => {
  if (!handler) {
    throw new Error('Transaction handler must be a function');
  }

  return client.$transaction(async (tx) => handler(tx), options);
};

export const resolveClient = <T extends PrismaClient | TransactionClient>(
  client: PrismaClient,
  tx?: TransactionClient,
): T => (tx ? (tx as T) : (client as unknown as T));
