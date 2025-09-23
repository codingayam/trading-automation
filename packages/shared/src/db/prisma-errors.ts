import { Prisma } from '@prisma/client';
import { UniqueConstraintViolationError } from '../errors.js';

export const isUniqueConstraintError = (error: unknown): error is Prisma.PrismaClientKnownRequestError =>
  error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2002';

export const rethrowKnownPrismaErrors = (error: unknown, message: string): never => {
  if (isUniqueConstraintError(error)) {
    const target = Array.isArray(error.meta?.target)
      ? (error.meta?.target as (string | number | symbol)[]).map(String)
      : undefined;

    throw new UniqueConstraintViolationError(message, {
      cause: error,
      target,
    });
  }

  throw error;
};
