import {
  createTradeRepository,
  getPrismaClient,
  type ListTradesParams,
  type ListTradesResult,
  type TradeRepository,
} from '@trading-automation/shared';

const prisma = getPrismaClient();
const defaultTradeRepository = createTradeRepository(prisma);
let tradeRepository: TradeRepository = defaultTradeRepository;

export interface TradeQueryParams {
  page?: number;
  pageSize?: number;
  symbol?: string;
  startDate?: Date;
  endDate?: Date;
}

export const listTrades = async (params: TradeQueryParams = {}): Promise<ListTradesResult> => {
  const query: ListTradesParams = {
    page: params.page,
    pageSize: params.pageSize,
    symbol: params.symbol,
    startDate: params.startDate,
    endDate: params.endDate,
    order: 'desc',
  };

  return tradeRepository.listTrades(query);
};

export const getTradeRepositoryForTesting = () => tradeRepository;

export const setTradeRepositoryForTesting = (repository: TradeRepository): void => {
  tradeRepository = repository;
};

export const resetTradeRepositoryForTesting = (): void => {
  tradeRepository = defaultTradeRepository;
};
