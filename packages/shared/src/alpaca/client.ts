import type { Logger } from '../logger.js';
import { httpFetch, type HttpFetchOptions } from '../http.js';
import {
  AlpacaError,
  AlpacaInsufficientBuyingPowerError,
  AlpacaOrderValidationError,
  type AlpacaErrorDetails,
  HttpRequestError,
} from '../errors.js';
import type {
  AlpacaAccount,
  AlpacaCalendarEntry,
  AlpacaClock,
  AlpacaLatestTradeResponse,
  AlpacaOrder,
  AlpacaPosition,
  SubmitAlpacaOrderRequest,
} from './types.js';

const DEFAULT_TIMEOUT_MS = 15_000;
const DEFAULT_POLL_TIMEOUT_MS = 60_000;
const MARKET_DATA_BASE_URL = 'https://data.alpaca.markets';

type SupportedResponse =
  | AlpacaOrder
  | AlpacaOrder[]
  | AlpacaAccount
  | AlpacaPosition[]
  | AlpacaLatestTradeResponse
  | AlpacaClock
  | AlpacaCalendarEntry[]
  | unknown;

export interface AlpacaClientOptions {
  key: string;
  secret: string;
  baseUrl: string;
  dataBaseUrl?: string;
  defaultTimeoutMs?: number;
  logger?: Logger;
}

export interface GetOrderParams {
  orderId: string;
}

export interface GetOrderByClientOrderIdParams {
  clientOrderId: string;
}

export interface SubmitOrderParams extends SubmitAlpacaOrderRequest {}

export interface GetLatestTradeParams {
  symbol: string;
}

export class AlpacaClient {
  private readonly key: string;
  private readonly secret: string;
  private readonly baseUrl: string;
  private readonly dataBaseUrl: string;
  private readonly logger?: Logger;
  private readonly defaultTimeoutMs: number;

  constructor(options: AlpacaClientOptions) {
    this.key = options.key;
    this.secret = options.secret;
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.dataBaseUrl = (options.dataBaseUrl ?? MARKET_DATA_BASE_URL).replace(/\/$/, '');
    this.logger = options.logger;
    this.defaultTimeoutMs = options.defaultTimeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  async submitOrder(params: SubmitOrderParams): Promise<AlpacaOrder> {
    return this.request<AlpacaOrder>('/v2/orders', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getOrder(params: GetOrderParams): Promise<AlpacaOrder> {
    return this.request<AlpacaOrder>(`/v2/orders/${params.orderId}`);
  }

  async getOrderByClientOrderId(params: GetOrderByClientOrderIdParams): Promise<AlpacaOrder> {
    return this.request<AlpacaOrder>(`/v2/orders:by_client_order_id?client_order_id=${encodeURIComponent(params.clientOrderId)}`);
  }

  async getAccount(): Promise<AlpacaAccount> {
    return this.request<AlpacaAccount>('/v2/account');
  }

  async getPositions(): Promise<AlpacaPosition[]> {
    return this.request<AlpacaPosition[]>('/v2/positions');
  }

  async getLatestTrade(params: GetLatestTradeParams): Promise<AlpacaLatestTradeResponse> {
    return this.request<AlpacaLatestTradeResponse>(`/v2/stocks/${encodeURIComponent(params.symbol)}/trades/latest`, {
      baseUrl: this.dataBaseUrl,
    });
  }

  async getClock(): Promise<AlpacaClock> {
    return this.request<AlpacaClock>('/v2/clock');
  }

  async getCalendar(params: { start?: string; end?: string; limit?: number } = {}): Promise<AlpacaCalendarEntry[]> {
    const searchParams = new URLSearchParams();

    if (params.start) {
      searchParams.set('start', params.start);
    }
    if (params.end) {
      searchParams.set('end', params.end);
    }
    if (typeof params.limit === 'number') {
      searchParams.set('limit', String(params.limit));
    }

    const query = searchParams.toString();
    const path = query ? `/v2/calendar?${query}` : '/v2/calendar';

    return this.request<AlpacaCalendarEntry[]>(path);
  }

  private async request<T extends SupportedResponse>(
    path: string,
    options: (HttpFetchOptions & { baseUrl?: string }) | undefined = undefined,
  ): Promise<T> {
    const { baseUrl, headers, timeoutMs, ...rest } = options ?? {};
    const url = `${(baseUrl ?? this.baseUrl).replace(/\/$/, '')}${path}`;

    const mergedHeaders: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'APCA-API-KEY-ID': this.key,
      'APCA-API-SECRET-KEY': this.secret,
      ...(headers as Record<string, string>),
    };

    try {
      const response = await httpFetch(url, {
        ...rest,
        headers: mergedHeaders,
        timeoutMs: timeoutMs ?? this.defaultTimeoutMs,
        logger: this.logger,
      });

      if (response.status === 204) {
        return undefined as T;
      }

      const text = await response.text();
      if (!text) {
        return undefined as T;
      }

      return JSON.parse(text) as T;
    } catch (error) {
      if (error instanceof AlpacaError) {
        throw error;
      }

      if (error instanceof HttpRequestError) {
        throw this.mapHttpError(error);
      }

      throw new AlpacaError('Unexpected error during Alpaca request', { status: 0 }, 'ALPACA_ERROR', error);
    }
  }

  private mapHttpError(error: HttpRequestError): AlpacaError {
    const response = error.response;

    if (!response) {
      return new AlpacaError(error.message, { status: 0 }, 'ALPACA_ERROR', error);
    }

    const { status, body } = response;
    const parsedBody = this.safeParseBody(body);
    const details: AlpacaErrorDetails = {
      status,
      errorCode: this.extractErrorCode(parsedBody),
      body: parsedBody,
    };

    const message = this.extractMessage(parsedBody) ?? `Alpaca request failed with status ${status}`;

    if (status === 422) {
      const violations = this.extractViolations(parsedBody);
      return new AlpacaOrderValidationError(message, { ...details, violations }, error);
    }

    if (status === 403 || status === 400) {
      if (typeof message === 'string' && /buying power/i.test(message)) {
        return new AlpacaInsufficientBuyingPowerError(message, details, error);
      }
    }

    return new AlpacaError(message, details, 'ALPACA_ERROR', error);
  }

  private safeParseBody(body?: string): unknown {
    if (!body) {
      return undefined;
    }

    try {
      return JSON.parse(body);
    } catch {
      return body;
    }
  }

  private extractMessage(body: unknown): string | undefined {
    if (!body || typeof body !== 'object') {
      if (typeof body === 'string') {
        return body;
      }
      return undefined;
    }

    const maybeMessage = (body as { message?: unknown }).message;
    if (typeof maybeMessage === 'string') {
      return maybeMessage;
    }

    return undefined;
  }

  private extractErrorCode(body: unknown): string | number | undefined {
    if (body && typeof body === 'object' && 'code' in body) {
      const code = (body as { code?: unknown }).code;
      if (typeof code === 'string' || typeof code === 'number') {
        return code;
      }
    }

    return undefined;
  }

  private extractViolations(body: unknown): string[] | undefined {
    if (!body || typeof body !== 'object') {
      return undefined;
    }

    const violations: string[] = [];
    const message = this.extractMessage(body);
    if (message) {
      violations.push(message);
    }

    const data = (body as { data?: unknown }).data;
    if (Array.isArray(data)) {
      for (const item of data) {
        if (item && typeof item === 'object') {
          const itemMessage = (item as { message?: unknown }).message;
          if (typeof itemMessage === 'string') {
            violations.push(itemMessage);
          }
        }
      }
    }

    return violations.length ? violations : undefined;
  }
}

export const createAlpacaClient = (options: AlpacaClientOptions): AlpacaClient => new AlpacaClient(options);

export const DEFAULT_ORDER_POLL_TIMEOUT_MS = DEFAULT_POLL_TIMEOUT_MS;
