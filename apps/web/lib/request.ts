import type { NextRequest } from 'next/server';

export const getClientAddress = (request: NextRequest): string => {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    const [first] = forwarded.split(',');
    if (first) {
      return first.trim();
    }
  }

  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp.trim();
  }

  return request.ip ?? '127.0.0.1';
};
