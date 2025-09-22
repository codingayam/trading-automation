import type { ZodIssue } from 'zod';

export type AppErrorCode =
  | 'ENV_VALIDATION'
  | 'HTTP_REQUEST_FAILED'
  | 'DB_UNIQUE_CONSTRAINT'
  | 'ALPACA_ERROR'
  | 'ALPACA_VALIDATION'
  | 'ALPACA_BUYING_POWER'
  | 'TRADE_GUARD_BLOCKED'
  | 'UNEXPECTED';

export interface AppErrorOptions {
  message: string;
  code?: AppErrorCode;
  cause?: unknown;
  details?: unknown;
}

export class AppError extends Error {
  readonly code: AppErrorCode;
  readonly details?: unknown;

  constructor({ message, code = 'UNEXPECTED', cause, details }: AppErrorOptions) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.details = details;
    if (cause) {
      this.cause = cause;
    }
  }
}

export interface EnvValidationDetails {
  target: 'worker' | 'web' | 'shared';
  issues: ZodIssue[];
}

export class EnvValidationError extends AppError {
  constructor(details: EnvValidationDetails) {
    const summary = details.issues
      .map((issue) => `${issue.path.join('.') || '(root)'}: ${issue.message}`)
      .join('; ');

    super({
      message: `Environment validation failed for ${details.target}: ${summary}`,
      code: 'ENV_VALIDATION',
      details,
    });

    this.name = 'EnvValidationError';
  }
}

export interface HttpRequestErrorOptions extends Partial<AppErrorOptions> {
  response?: {
    status: number;
    statusText: string;
    url: string;
    body?: string;
  };
}

export class HttpRequestError extends AppError {
  readonly response?: HttpRequestErrorOptions['response'];

  constructor(message: string, options: HttpRequestErrorOptions = {}) {
    super({
      message,
      code: 'HTTP_REQUEST_FAILED',
      cause: options.cause,
      details: options.details ?? options.response,
    });
    this.name = 'HttpRequestError';
    this.response = options.response;
  }
}

export interface UniqueConstraintViolationOptions {
  cause?: unknown;
  target?: string[];
}

export class UniqueConstraintViolationError extends AppError {
  readonly target?: string[];

  constructor(message: string, options: UniqueConstraintViolationOptions = {}) {
    super({
      message,
      code: 'DB_UNIQUE_CONSTRAINT',
      cause: options.cause,
      details: options.target ? { target: options.target } : undefined,
    });
    this.name = 'UniqueConstraintViolationError';
    this.target = options.target;
  }
}

export interface AlpacaErrorDetails {
  status: number;
  errorCode?: string | number;
  body?: unknown;
  requestId?: string;
}

export class AlpacaError extends AppError {
  readonly status: number;
  readonly errorCode?: string | number;
  readonly requestId?: string;

  constructor(message: string, details: AlpacaErrorDetails, code: AppErrorCode = 'ALPACA_ERROR', cause?: unknown) {
    super({ message, code, cause, details });
    this.name = 'AlpacaError';
    this.status = details.status;
    this.errorCode = details.errorCode;
    this.requestId = details.requestId;
  }
}

export class AlpacaOrderValidationError extends AlpacaError {
  readonly violations?: string[];

  constructor(message: string, details: AlpacaErrorDetails & { violations?: string[] }, cause?: unknown) {
    super(message, details, 'ALPACA_VALIDATION', cause);
    this.name = 'AlpacaOrderValidationError';
    this.violations = details.violations;
  }
}

export class AlpacaInsufficientBuyingPowerError extends AlpacaError {
  constructor(message: string, details: AlpacaErrorDetails, cause?: unknown) {
    super(message, details, 'ALPACA_BUYING_POWER', cause);
    this.name = 'AlpacaInsufficientBuyingPowerError';
  }
}

export interface TradeGuardrailErrorDetails {
  guard: string;
  context?: Record<string, unknown>;
}

export class TradeGuardrailError extends AppError {
  readonly guard: string;
  readonly context?: Record<string, unknown>;

  constructor(message: string, details: TradeGuardrailErrorDetails) {
    super({
      message,
      code: 'TRADE_GUARD_BLOCKED',
      details,
    });
    this.name = 'TradeGuardrailError';
    this.guard = details.guard;
    this.context = details.context;
  }
}
