export interface QuiverCongressTradingRecord {
  Ticker: string;
  Name: string;
  Transaction: string;
  Filed: string;
  Traded?: string;
  Party?: string;
  [key: string]: unknown;
}

export type QuiverCongressTradingResponse = QuiverCongressTradingRecord[];
