export interface RateLimitOptions {
  windowMs: number;
  max: number;
}

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  limit: number;
  retryAfterMs?: number;
}

interface Bucket {
  count: number;
  expiresAt: number;
}

export class MemoryRateLimiter {
  private readonly buckets = new Map<string, Bucket>();

  constructor(private readonly options: RateLimitOptions) {}

  consume(key: string, now = Date.now()): RateLimitResult {
    const { windowMs, max } = this.options;

    const bucket = this.buckets.get(key);

    if (!bucket || bucket.expiresAt <= now) {
      this.buckets.set(key, { count: 1, expiresAt: now + windowMs });
      return { allowed: true, remaining: max - 1, limit: max };
    }

    if (bucket.count >= max) {
      return {
        allowed: false,
        remaining: 0,
        limit: max,
        retryAfterMs: bucket.expiresAt - now,
      };
    }

    bucket.count += 1;
    return { allowed: true, remaining: max - bucket.count, limit: max };
  }

  reset(): void {
    this.buckets.clear();
  }
}

const defaultLimiter = new MemoryRateLimiter({ windowMs: 60_000, max: 30 });

export const applyRateLimit = (key: string): RateLimitResult => defaultLimiter.consume(key);

export const resetDefaultRateLimiter = (): void => defaultLimiter.reset();
