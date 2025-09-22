import { HttpRequestError } from './errors';
import type { Logger } from './logger';

const DEFAULT_RETRY_STATUS = [408, 425, 429, 500, 502, 503, 504];

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export interface HttpFetchOptions extends RequestInit {
  retries?: number;
  retryDelayMs?: number;
  retryBackoffFactor?: number;
  retryOn?: number[] | ((response: Response) => boolean | Promise<boolean>);
  timeoutMs?: number;
  logger?: Logger;
}

const shouldRetryResponse = async (
  response: Response,
  retryOn: HttpFetchOptions['retryOn'],
): Promise<boolean> => {
  if (typeof retryOn === 'function') {
    return retryOn(response);
  }

  const retryStatuses = retryOn ?? DEFAULT_RETRY_STATUS;
  return retryStatuses.includes(response.status);
};

const resolveUrl = (input: RequestInfo | URL): string | undefined => {
  if (typeof input === 'string') {
    return input;
  }

  if (input instanceof URL) {
    return input.toString();
  }

  if (typeof Request !== 'undefined' && input instanceof Request) {
    return input.url;
  }

  return undefined;
};

export const httpFetch = async (
  input: RequestInfo | URL,
  options: HttpFetchOptions = {},
): Promise<Response> => {
  const {
    retries = 2,
    retryDelayMs = 250,
    retryBackoffFactor = 2,
    retryOn = DEFAULT_RETRY_STATUS,
    timeoutMs,
    logger,
    signal,
    ...rest
  } = options;

  let attempt = 0;
  let delayMs = retryDelayMs;

  while (attempt <= retries) {
    attempt += 1;

    const controller = new AbortController();
    const cleanupCallbacks: Array<() => void> = [];
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    const forwardAbort = (source: AbortSignal) => {
      if (source.aborted) {
        controller.abort(source.reason);
        return;
      }

      const handler = () => controller.abort(source.reason);
      source.addEventListener('abort', handler, { once: true });
      cleanupCallbacks.push(() => source.removeEventListener('abort', handler));
    };

    const externalSignals = [signal].filter(
      (value): value is AbortSignal => Boolean(value),
    );

    externalSignals.forEach(forwardAbort);

    if (timeoutMs) {
      timeoutId = setTimeout(() => {
        controller.abort(new DOMException('Request timed out', 'TimeoutError'));
      }, timeoutMs);
    }

    const requestInit: RequestInit = { ...rest, signal: controller.signal };

    try {
      const response = await fetch(input, requestInit);

      if (!response.ok) {
        const retryable = await shouldRetryResponse(response, retryOn);

        if (retryable && attempt <= retries) {
          logger?.warn(
            { attempt, status: response.status, url: response.url },
            'Retrying HTTP request due to response status',
          );
          await sleep(delayMs);
          delayMs *= retryBackoffFactor;
          continue;
        }

        const bodySample = await response
          .clone()
          .text()
          .then((text) => text.slice(0, 1024))
          .catch(() => undefined);

        throw new HttpRequestError(`Request failed with status ${response.status}`, {
          response: {
            status: response.status,
            statusText: response.statusText,
            url: response.url,
            body: bodySample,
          },
        });
      }

      return response;
    } catch (error) {
      const aborted = controller.signal.aborted;

      if (!aborted && attempt <= retries) {
        logger?.warn(
          { attempt, error, url: resolveUrl(input) },
          'Retrying HTTP request after exception',
        );
        await sleep(delayMs);
        delayMs *= retryBackoffFactor;
        continue;
      }

      if (error instanceof HttpRequestError) {
        throw error;
      }

      throw new HttpRequestError('HTTP request failed', {
        cause: error,
        details: {
          url: resolveUrl(input),
        },
      });
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      cleanupCallbacks.forEach((cleanup) => cleanup());
    }
  }

  throw new HttpRequestError('HTTP request failed after exhausting retries', {
    details: {
      url: resolveUrl(input),
      retries,
    },
  });
};
