import { prisma } from '../src/db';
import { Prisma } from '@prisma/client';

const quiverSample = [
  {
    id: 'feed-sample-1',
    ticker: 'NVDA',
    memberName: 'John Doe',
    transaction: 'BUY' as const,
    tradeDate: new Date('2024-02-15T00:00:00Z'),
    filingDate: new Date('2024-02-16T15:30:00Z'),
    party: 'DEMOCRAT' as const,
    rawJson: {
      Ticker: 'NVDA',
      Name: 'John Doe',
      Transaction: 'Purchase',
      Traded: '2024-02-15',
      Filed: '2024-02-16',
      Party: 'D',
      Amount: '$1,001 - $15,000',
    },
  },
  {
    id: 'feed-sample-2',
    ticker: 'AAPL',
    memberName: 'Jane Smith',
    transaction: 'BUY' as const,
    tradeDate: new Date('2024-02-14T00:00:00Z'),
    filingDate: new Date('2024-02-15T12:00:00Z'),
    party: 'REPUBLICAN' as const,
    rawJson: {
      Ticker: 'AAPL',
      Name: 'Jane Smith',
      Transaction: 'Purchase',
      Traded: '2024-02-14',
      Filed: '2024-02-15',
      Party: 'R',
      Amount: '$15,001 - $50,000',
    },
  },
];

const tradesSample = [
  {
    sourceHash: 'john-doe|NVDA|2024-02-16|BUY',
    symbol: 'NVDA',
    status: 'ACCEPTED' as const,
    notionalSubmitted: new Prisma.Decimal(1000),
    clientOrderId: 'cmplx-open-job-1',
    alpacaOrderId: 'order-nvda-1',
    congressTradeFeedId: 'feed-sample-1',
    submittedAt: new Date('2024-02-16T14:35:00Z'),
    rawOrderJson: {
      id: 'order-nvda-1',
      status: 'accepted',
    },
  },
  {
    sourceHash: 'jane-smith|AAPL|2024-02-15|BUY',
    symbol: 'AAPL',
    status: 'FILLED' as const,
    notionalSubmitted: new Prisma.Decimal(1000),
    filledQty: new Prisma.Decimal(5.1234),
    filledAvgPrice: new Prisma.Decimal(195.12),
    clientOrderId: 'cmplx-open-job-2',
    alpacaOrderId: 'order-aapl-2',
    congressTradeFeedId: 'feed-sample-2',
    submittedAt: new Date('2024-02-15T13:05:00Z'),
    filledAt: new Date('2024-02-15T13:07:00Z'),
    rawOrderJson: {
      id: 'order-aapl-2',
      status: 'filled',
    },
  },
];

async function main(): Promise<void> {
  await prisma.$transaction([
    prisma.trade.deleteMany(),
    prisma.congressTradeFeed.deleteMany(),
    prisma.jobRun.deleteMany(),
    prisma.ingestCheckpoint.deleteMany(),
  ]);

  await prisma.congressTradeFeed.createMany({ data: quiverSample });

  for (const trade of tradesSample) {
    await prisma.trade.create({ data: trade });
  }

  await prisma.jobRun.create({
    data: {
      type: 'OPEN_JOB',
      tradingDateEt: new Date('2024-02-16T00:00:00-05:00'),
      status: 'SUCCESS',
      startedAt: new Date('2024-02-16T14:30:00Z'),
      finishedAt: new Date('2024-02-16T14:31:30Z'),
      summaryJson: {
        filingsProcessed: 2,
        tradesSubmitted: 2,
        tradesFilled: 1,
      },
    },
  });

  await prisma.ingestCheckpoint.create({
    data: {
      tradingDateEt: new Date('2024-02-16T00:00:00-05:00'),
      lastFiledTsProcessedEt: new Date('2024-02-16T14:00:00Z'),
    },
  });
}

main()
  .then(() => {
    // eslint-disable-next-line no-console
    console.log('Database seed data loaded');
  })
  .catch((error) => {
    console.error('Failed to seed database', error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
