import { createHash } from 'node:crypto';

import type { CongressParty, CongressTradeTransaction, Prisma } from '@prisma/client';

import {
  AlpacaClient,
  type GuardrailConfig,
  QuiverClient,
  type QuiverCongressTradingRecord,
  addEasternDays,
  createEasternDate,
  createIngestCheckpointRepository,
  createJobRunRepository,
  createTradeRepository,
  createCongressTradeFeedRepository,
  endOfEasternDay,
  ensureDate,
  formatDateKey,
  getPrismaClient,
  isWithinRange,
  parseQuiverDate,
  startOfEasternDay,
  submitTradeForFiling,
  type WorkerEnv,
} from '@trading-automation/shared';

import type { Logger } from '@trading-automation/shared';
import { UniqueConstraintViolationError } from '@trading-automation/shared';

interface RunOpenJobOptions {
  env: Readonly<WorkerEnv>;
  logger: Logger;
  dryRun?: boolean;
  now?: () => Date;
}

interface FilingWindow {
  label: 'previous' | 'current';
  start: Date;
  end: Date;
}

interface FilingCandidate {
  sourceHash: string;
  ticker: string;
  memberName: string;
  transaction: CongressTradeTransaction;
  tradeDate: Date;
  filingDate: Date;
  party: CongressParty | null;
  raw: QuiverCongressTradingRecord;
  feedId: string;
  windowLabel: FilingWindow['label'];
}

interface FilingWindowSummary {
  label: FilingWindow['label'];
  start: string;
  end: string;
  filingsFetched: number;
  filingsConsidered: number;
  missingFields: number;
  outsideWindow: number;
  nonBuyFilings: number;
  duplicates: number;
}

interface TradeSummary {
  attempted: number;
  submitted: number;
  filled: number;
  fallbackUsed: number;
  guardrailBlocked: number;
  dryRunSkipped: number;
  failures: number;
}

interface JobRunSummary {
  dryRun: boolean;
  tradingDateEt: string;
  previousTradingDateEt: string | null;
  clock: unknown;
  calendar: {
    date: string;
    open: string | null;
    close: string | null;
    sessionOpen: string | null;
    sessionClose: string | null;
  } | null;
  windows: FilingWindowSummary[];
  trades: TradeSummary;
  checkpointUpdates: {
    previous: string | null;
    current: string | null;
  };
  errors: Array<{ message: string; context?: Record<string, unknown> }>;
}

interface RunOpenJobResult {
  status: 'success' | 'skipped' | 'failed';
  summary: JobRunSummary;
}

const toUpperTicker = (value: string | null | undefined): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed.toUpperCase() : null;
};

const normalizeMemberName = (value: string | null | undefined): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed || null;
};

const normalizeTransaction = (value: string | null | undefined): CongressTradeTransaction => {
  if (!value) {
    return 'UNKNOWN';
  }

  const normalized = value.trim().toLowerCase();

  if (normalized.includes('purchase') || normalized === 'buy') {
    return 'BUY';
  }

  if (normalized.includes('sale') || normalized.includes('sell')) {
    return 'SELL';
  }

  return 'UNKNOWN';
};

const normalizeParty = (value: string | null | undefined): CongressParty | null => {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toUpperCase();

  if (normalized === 'D' || normalized === 'DEM' || normalized === 'DEMOCRAT') {
    return 'DEMOCRAT';
  }

  if (normalized === 'R' || normalized === 'REP' || normalized === 'REPUBLICAN') {
    return 'REPUBLICAN';
  }

  if (normalized === 'I' || normalized === 'IND') {
    return 'INDEPENDENT';
  }

  if (normalized === 'O' || normalized === 'OTHER') {
    return 'OTHER';
  }

  return 'UNKNOWN';
};

const serializeError = (error: unknown) => {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
    };
  }

  if (typeof error === 'object' && error !== null) {
    return error;
  }

  return { value: error };
};

const buildSourceHash = (name: string, ticker: string, filed: Date, transaction: CongressTradeTransaction): string => {
  const filedKey = filed.toISOString();
  const raw = `${name}|${ticker}|${filedKey}|${transaction}`;
  return createHash('sha256').update(raw).digest('hex');
};

const toInputJsonValue = (value: unknown): Prisma.InputJsonValue => value as Prisma.InputJsonValue;

const parseCalendarTime = (date: string, time: string | null | undefined): Date => {
  const safeTime = (time ?? '09:30').trim();
  const [hourString = '09', minuteString = '30', secondString = '00'] = safeTime.split(':');
  const [yearString, monthString, dayString] = date.split('-');

  const year = Number(yearString);
  const month = Number(monthString);
  const day = Number(dayString);
  const hour = Number(hourString);
  const minute = Number(minuteString);
  const second = Number(secondString ?? '0');

  return createEasternDate(year, month, day, hour, minute, second, 0);
};

const buildWindowSummary = (window: FilingWindow): FilingWindowSummary => ({
  label: window.label,
  start: window.start.toISOString(),
  end: window.end.toISOString(),
  filingsFetched: 0,
  filingsConsidered: 0,
  missingFields: 0,
  outsideWindow: 0,
  nonBuyFilings: 0,
  duplicates: 0,
});

const createGuardrailConfig = (env: Readonly<WorkerEnv>): GuardrailConfig => ({
  tradingEnabled: env.TRADING_ENABLED,
  paperTrading: env.PAPER_TRADING,
  tradeNotionalUsd: env.TRADE_NOTIONAL_USD,
  dailyMaxFilings: env.DAILY_MAX_FILINGS ?? undefined,
  perTickerDailyMax: env.PER_TICKER_DAILY_MAX ?? undefined,
});

const collectDatesForWindow = (window: FilingWindow): Date[] => {
  const dates: Date[] = [];
  let cursor = startOfEasternDay(window.start);
  const end = startOfEasternDay(window.end);

  while (cursor.getTime() <= end.getTime()) {
    dates.push(cursor);
    cursor = addEasternDays(cursor, 1);
  }

  return dates;
};

const toJobRunSummary = (params: {
  dryRun: boolean;
  tradingDateEt: Date;
  previousTradingDateEt: Date | null;
  clock: unknown;
  calendarEntry: {
    date: string;
    open: string | null;
    close: string | null;
    session_open?: string | null;
    session_close?: string | null;
  } | null;
  windowSummaries: FilingWindowSummary[];
  tradeSummary: TradeSummary;
  checkpointUpdates: { previous: Date | null; current: Date | null };
  errors: Array<{ message: string; context?: Record<string, unknown> }>;
}): JobRunSummary => ({
  dryRun: params.dryRun,
  tradingDateEt: formatDateKey(params.tradingDateEt),
  previousTradingDateEt: params.previousTradingDateEt ? formatDateKey(params.previousTradingDateEt) : null,
  clock: params.clock,
  calendar: params.calendarEntry
    ? {
        date: params.calendarEntry.date,
        open: params.calendarEntry.open ?? null,
        close: params.calendarEntry.close ?? null,
        sessionOpen: params.calendarEntry.session_open ?? null,
        sessionClose: params.calendarEntry.session_close ?? null,
      }
    : null,
  windows: params.windowSummaries,
  trades: params.tradeSummary,
  checkpointUpdates: {
    previous: params.checkpointUpdates.previous?.toISOString() ?? null,
    current: params.checkpointUpdates.current?.toISOString() ?? null,
  },
  errors: params.errors,
});

export const runOpenJob = async (options: RunOpenJobOptions): Promise<RunOpenJobResult> => {
  const { env, logger, dryRun = false, now = () => new Date() } = options;

  const prisma = getPrismaClient();
  const guardrailConfig = createGuardrailConfig(env);

  const jobRunRepository = createJobRunRepository(prisma);
  const checkpointRepository = createIngestCheckpointRepository(prisma);
  const tradeRepository = createTradeRepository(prisma);
  const feedRepository = createCongressTradeFeedRepository(prisma);

  const alpacaClient = new AlpacaClient({
    key: env.ALPACA_KEY_ID,
    secret: env.ALPACA_SECRET_KEY,
    baseUrl: env.ALPACA_BASE_URL,
    dataBaseUrl: env.ALPACA_DATA_BASE_URL,
    logger,
  });

  const quiverClient = new QuiverClient({
    apiKey: env.QUIVER_API_KEY,
    baseUrl: env.QUIVER_BASE_URL,
    logger,
  });

  const errors: Array<{ message: string; context?: Record<string, unknown> }> = [];

  const clock = await alpacaClient.getClock();
  const tradingDateEt = startOfEasternDay(ensureDate(clock.timestamp));
  const tradingDateKey = formatDateKey(tradingDateEt);

  if (!clock.is_open) {
    logger.info({ tradingDateKey, clock }, 'Market is not open; skipping open-job execution');
    return {
      status: 'skipped',
      summary: toJobRunSummary({
        dryRun,
        tradingDateEt,
        previousTradingDateEt: null,
        clock,
        calendarEntry: null,
        windowSummaries: [],
        tradeSummary: {
          attempted: 0,
          submitted: 0,
          filled: 0,
          fallbackUsed: 0,
          guardrailBlocked: 0,
          dryRunSkipped: 0,
          failures: 0,
        },
        checkpointUpdates: { previous: null, current: null },
        errors: [],
      }),
    };
  }

  const existingRun = await jobRunRepository.getByTradingDate(tradingDateEt);

  if (existingRun && existingRun.status !== 'FAILED') {
    logger.warn({ tradingDateKey, existingRunId: existingRun.id }, 'Job run already exists for trading date; skipping execution');
    return {
      status: 'skipped',
      summary: toJobRunSummary({
        dryRun,
        tradingDateEt,
        previousTradingDateEt: null,
        clock,
        calendarEntry: null,
        windowSummaries: [],
        tradeSummary: {
          attempted: 0,
          submitted: 0,
          filled: 0,
          fallbackUsed: 0,
          guardrailBlocked: 0,
          dryRunSkipped: 0,
          failures: 0,
        },
        checkpointUpdates: { previous: null, current: null },
        errors: [],
      }),
    };
  }

  const calendarStart = formatDateKey(addEasternDays(tradingDateEt, -7));
  const calendarEntries = await alpacaClient.getCalendar({ start: calendarStart, end: tradingDateKey });
  const calendarEntry = calendarEntries.find((entry) => entry.date === tradingDateKey);

  if (!calendarEntry) {
    logger.warn({ tradingDateKey }, 'No Alpaca calendar entry found for trading date; skipping execution');
    return {
      status: 'skipped',
      summary: toJobRunSummary({
        dryRun,
        tradingDateEt,
        previousTradingDateEt: null,
        clock,
        calendarEntry: null,
        windowSummaries: [],
        tradeSummary: {
          attempted: 0,
          submitted: 0,
          filled: 0,
          fallbackUsed: 0,
          guardrailBlocked: 0,
          dryRunSkipped: 0,
          failures: 0,
        },
        checkpointUpdates: { previous: null, current: null },
        errors: [{ message: 'Missing calendar entry for trading date' }],
      }),
    };
  }

  const currentIndex = calendarEntries.findIndex((entry) => entry.date === tradingDateKey);
  const previousEntry = currentIndex > 0 ? calendarEntries[currentIndex - 1] : null;
  const previousTradingDateEt = previousEntry ? startOfEasternDay(ensureDate(previousEntry.date)) : null;

  if (!previousTradingDateEt) {
    logger.warn({ tradingDateKey }, 'Unable to determine previous trading date; skipping execution');
    return {
      status: 'skipped',
      summary: toJobRunSummary({
        dryRun,
        tradingDateEt,
        previousTradingDateEt: null,
        clock,
        calendarEntry,
        windowSummaries: [],
        tradeSummary: {
          attempted: 0,
          submitted: 0,
          filled: 0,
          fallbackUsed: 0,
          guardrailBlocked: 0,
          dryRunSkipped: 0,
          failures: 0,
        },
        checkpointUpdates: { previous: null, current: null },
        errors: [{ message: 'Missing previous trading date in Alpaca calendar' }],
      }),
    };
  }

  if (!dryRun) {
    const jobRun = await jobRunRepository.start({ tradingDateEt, summaryJson: { initiatedAt: now().toISOString() } });
    logger.info({ tradingDateKey, jobRunId: jobRun.id }, 'Started open-job execution');
  } else {
    logger.info({ tradingDateKey }, 'Dry-run enabled; skipping job-run persistence');
  }

  const previousCheckpoint = await checkpointRepository.get(previousTradingDateEt);
  const currentCheckpoint = await checkpointRepository.get(tradingDateEt);

  const previousWindow: FilingWindow = {
    label: 'previous',
    start: previousCheckpoint?.lastFiledTsProcessedEt
      ? new Date(previousCheckpoint.lastFiledTsProcessedEt.getTime() + 1)
      : startOfEasternDay(previousTradingDateEt),
    end: endOfEasternDay(previousTradingDateEt),
  };

  const currentOpenTime = parseCalendarTime(calendarEntry.date, calendarEntry.open ?? calendarEntry.session_open ?? null);

  const currentWindow: FilingWindow = {
    label: 'current',
    start: currentCheckpoint?.lastFiledTsProcessedEt
      ? new Date(currentCheckpoint.lastFiledTsProcessedEt.getTime() + 1)
      : startOfEasternDay(tradingDateEt),
    end: currentOpenTime,
  };

  const windowSummaries = [buildWindowSummary(previousWindow), buildWindowSummary(currentWindow)];
  const filingCandidates: FilingCandidate[] = [];
  const seenSources = new Set<string>();

  const processWindow = async (window: FilingWindow, summary: FilingWindowSummary) => {
    const datesToFetch = collectDatesForWindow(window);

    for (const date of datesToFetch) {
      let records: QuiverCongressTradingRecord[];

      try {
        records = await quiverClient.getCongressTradingByDate({ date });
      } catch (error) {
        const message = `Quiver fetch failed for ${formatDateKey(date)} (${window.label})`;
        throw new Error(message, { cause: error as Error });
      }

      summary.filingsFetched += records.length;

      for (const record of records) {
        const ticker = toUpperTicker(record.Ticker);
        const memberName = normalizeMemberName(record.Name);
        const filingDate = parseQuiverDate(record.Filed);

        if (!ticker || !memberName || !filingDate) {
          summary.missingFields += 1;
          continue;
        }

        if (!isWithinRange(filingDate, window.start, window.end)) {
          summary.outsideWindow += 1;
          continue;
        }

        const transaction = normalizeTransaction(record.Transaction);

        if (transaction !== 'BUY') {
          summary.nonBuyFilings += 1;
          continue;
        }

        const tradeDate = parseQuiverDate(record.Traded) ?? filingDate;
        const party = normalizeParty(record.Party);
        const sourceHash = buildSourceHash(memberName, ticker, filingDate, transaction);
        const feedId = sourceHash;

        if (seenSources.has(sourceHash)) {
          summary.duplicates += 1;
          continue;
        }

        seenSources.add(sourceHash);

        summary.filingsConsidered += 1;

        filingCandidates.push({
          sourceHash,
          ticker,
          memberName,
          transaction,
          tradeDate,
          filingDate,
          party,
          raw: record,
          feedId,
          windowLabel: window.label,
        });
      }
    }
  };


  let windowProcessingFailed = false;
  let checkpointUpdates: { previous: Date | null; current: Date | null } = { previous: null, current: null };

  try {
    await processWindow(previousWindow, windowSummaries[0]);
    await processWindow(currentWindow, windowSummaries[1]);
  } catch (error) {
    windowProcessingFailed = true;
    errors.push({
      message: 'Failed to collect Quiver filings for trading windows',
      context: { error: serializeError(error) },
    });
    logger.error({ err: error }, 'Encountered error while collecting Quiver filings');
  }

  const tradeSummary: TradeSummary = {
    attempted: 0,
    submitted: 0,
    filled: 0,
    fallbackUsed: 0,
    guardrailBlocked: 0,
    dryRunSkipped: 0,
    failures: 0,
  };

  const tradingWindowStart = startOfEasternDay(tradingDateEt);
  const tradingWindowEnd = endOfEasternDay(tradingDateEt);

  try {
    logger.info(
      {
        tradingDateKey,
        candidates: filingCandidates.length,
        previousWindow: windowSummaries[0],
        currentWindow: windowSummaries[1],
        windowProcessingFailed,
      },
      'Collected filing candidates for trade submission',
    );

    if (windowProcessingFailed) {
      logger.warn('Skipping trade submission because filing collection failed');
    }

    for (const candidate of windowProcessingFailed ? [] : filingCandidates) {
      tradeSummary.attempted += 1;

      if (dryRun) {
        tradeSummary.dryRunSkipped += 1;
        logger.info(
          { ticker: candidate.ticker, sourceHash: candidate.sourceHash },
          'Dry-run enabled; skipping trade persistence and submission',
        );
        continue;
      }

      let feedRecord;

      try {
        feedRecord = await feedRepository.create({
          id: candidate.feedId,
          ticker: candidate.ticker,
          memberName: candidate.memberName,
          transaction: candidate.transaction,
          tradeDate: candidate.tradeDate,
          filingDate: candidate.filingDate,
          party: candidate.party,
          rawJson: toInputJsonValue(candidate.raw),
        });
      } catch (error) {
        if (error instanceof UniqueConstraintViolationError) {
          feedRecord = await feedRepository.findById(candidate.feedId);
        } else {
          throw error;
        }
      }

      if (!feedRecord) {
        errors.push({
          message: 'Failed to persist or retrieve congress trade feed record',
          context: { sourceHash: candidate.sourceHash },
        });
        tradeSummary.failures += 1;
        continue;
      }

      try {
        const tradeResult = await submitTradeForFiling({
          alpacaClient,
          tradeRepository,
          prismaClient: prisma,
          guardrailConfig,
          sourceHash: candidate.sourceHash,
          symbol: candidate.ticker,
          congressTradeFeedId: feedRecord.id,
          tradingDateWindowStart: tradingWindowStart,
          tradingDateWindowEnd: tradingWindowEnd,
          logger,
        });

        if (tradeResult.guardrailBlocked) {
          tradeSummary.guardrailBlocked += 1;
        } else if (tradeResult.status === 'failed') {
          tradeSummary.failures += 1;
        } else {
          tradeSummary.submitted += 1;
          if (tradeResult.status === 'FILLED') {
            tradeSummary.filled += 1;
          }
        }

        if (!tradeResult.guardrailBlocked && tradeResult.fallbackUsed) {
          tradeSummary.fallbackUsed += 1;
        }
      } catch (error) {
        tradeSummary.failures += 1;
        errors.push({
          message: error instanceof Error ? error.message : 'Trade submission failed',
          context: {
            ticker: candidate.ticker,
            sourceHash: candidate.sourceHash,
            error: serializeError(error),
          },
        });
        logger.error({ err: error, ticker: candidate.ticker, sourceHash: candidate.sourceHash }, 'Trade submission encountered error');
      }
    }

    checkpointUpdates = {
      previous: windowProcessingFailed ? null : previousWindow.end,
      current: windowProcessingFailed ? null : currentWindow.end,
    };

    if (!dryRun && !windowProcessingFailed) {
      try {
        await checkpointRepository.upsert({
          tradingDateEt: previousTradingDateEt,
          lastFiledTsProcessedEt: previousWindow.end,
        });

        await checkpointRepository.upsert({
          tradingDateEt,
          lastFiledTsProcessedEt: currentWindow.end,
        });
      } catch (error) {
        errors.push({
          message: 'Failed to update ingest checkpoints',
          context: { error: serializeError(error) },
        });
      }
    }

    const summary = toJobRunSummary({
      dryRun,
      tradingDateEt,
      previousTradingDateEt,
      clock,
      calendarEntry,
      windowSummaries,
      tradeSummary,
      checkpointUpdates,
      errors,
    });

    if (errors.length > 0 || tradeSummary.failures > 0) {
      if (!dryRun) {
        await jobRunRepository.fail({ tradingDateEt, summaryJson: toInputJsonValue(summary) });
      }
      return {
        status: 'failed',
        summary,
      };
    }

    if (!dryRun) {
      await jobRunRepository.complete({ tradingDateEt, summaryJson: toInputJsonValue(summary) });
    }

    return {
      status: 'success',
      summary,
    };
  } catch (error) {
    errors.push({
      message: 'Unexpected error during open-job execution',
      context: { error: serializeError(error) },
    });
    logger.error({ err: error }, 'Open-job execution aborted unexpectedly');

    const summary = toJobRunSummary({
      dryRun,
      tradingDateEt,
      previousTradingDateEt,
      clock,
      calendarEntry,
      windowSummaries,
      tradeSummary,
      checkpointUpdates,
      errors,
    });

    if (!dryRun) {
      await jobRunRepository.fail({ tradingDateEt, summaryJson: toInputJsonValue(summary) });
    }

    return {
      status: 'failed',
      summary,
    };
  }
};
