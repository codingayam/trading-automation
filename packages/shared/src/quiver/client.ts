import type { Logger } from '../logger.js';
import { httpFetch, type HttpFetchOptions } from '../http.js';
import { ensureDate, formatDateKeyCompact } from '../time/index.js';
import type { QuiverCongressTradingRecord, QuiverCongressTradingResponse } from './types.js';

const DEFAULT_TIMEOUT_MS = 15000;

export interface QuiverClientOptions {
  apiKey: string;
  baseUrl: string;
  defaultTimeoutMs?: number;
  logger?: Logger;
}

export interface GetCongressTradingByDateParams {
  date: Date | string;
}

export class QuiverClient {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly logger?: Logger;
  private readonly defaultTimeoutMs: number;

  constructor(options: QuiverClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.logger = options.logger;
    this.defaultTimeoutMs = options.defaultTimeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  async getCongressTradingByDate(params: GetCongressTradingByDateParams): Promise<QuiverCongressTradingRecord[]> {
    const date = ensureDate(params.date);
    const dateParam = formatDateKeyCompact(date);
    const path = `/bulk/congresstrading?date=${encodeURIComponent(dateParam)}`;

    const response = await this.request(path, {
      headers: {
        Accept: 'application/json',
      },
    });

    const text = await response.text();

    if (!text) {
      return [];
    }

    const data = JSON.parse(text) as QuiverCongressTradingResponse;

    if (!Array.isArray(data)) {
      this.logger?.warn({ date: dateParam, body: data }, 'Unexpected Quiver response payload shape');
      return [];
    }

    return data;
  }

  private async request(path: string, options: HttpFetchOptions = {}): Promise<Response> {
    const url = `${this.baseUrl}${path}`;

    return httpFetch(url, {
      ...options,
      timeoutMs: options.timeoutMs ?? this.defaultTimeoutMs,
      headers: {
        ...(options.headers as Record<string, string>),
        Authorization: `Bearer ${this.apiKey}`,
      },
      logger: this.logger,
    });
  }
}
