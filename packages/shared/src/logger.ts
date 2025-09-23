import { pino } from 'pino';
import type { DestinationStream, Logger, LoggerOptions } from 'pino';

export interface CreateLoggerOptions extends LoggerOptions {
  destination?: DestinationStream;
}

export const createLogger = (options: CreateLoggerOptions = {}): Logger => {
  const { destination, level = (process.env.LOG_LEVEL as LoggerOptions['level']) ?? 'info', ...rest } =
    options;

  return pino({ level, ...rest }, destination);
};

export type { Logger } from 'pino';
