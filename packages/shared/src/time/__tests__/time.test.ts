import { describe, expect, it } from 'vitest';

import {
  addEasternDays,
  createEasternDate,
  endOfEasternDay,
  ensureDate,
  formatDateKey,
  formatDateKeyCompact,
  isWithinRange,
  parseQuiverDate,
  startOfEasternDay,
} from '../index';

const iso = (value: Date) => value.toISOString();

describe('time utilities', () => {
  it('creates Eastern-local timestamps respecting DST boundaries', () => {
    const summer = createEasternDate(2024, 6, 18, 9, 30);
    expect(iso(summer)).toBe('2024-06-18T13:30:00.000Z');

    const winter = createEasternDate(2024, 12, 2, 9, 30);
    expect(iso(winter)).toBe('2024-12-02T14:30:00.000Z');
  });

  it('computes start and end of Eastern day with DST awareness', () => {
    const reference = new Date('2024-03-11T12:00:00Z');
    const start = startOfEasternDay(reference);
    const end = endOfEasternDay(reference);

    expect(iso(start)).toBe('2024-03-11T04:00:00.000Z');
    expect(iso(end)).toBe('2024-03-12T03:59:59.999Z');
  });

  it('parses Quiver date strings as Eastern midnight when no time is provided', () => {
    const parsed = parseQuiverDate('2025-09-17');
    expect(parsed).not.toBeNull();
    expect(iso(parsed!)).toBe('2025-09-17T04:00:00.000Z');
  });

  it('parses ISO timestamp strings without altering timezone', () => {
    const parsed = parseQuiverDate('2025-09-17T10:15:00Z');
    expect(parsed).not.toBeNull();
    expect(iso(parsed!)).toBe('2025-09-17T10:15:00.000Z');
  });

  it('formats Eastern dates as calendar keys', () => {
    const date = createEasternDate(2024, 10, 4, 12, 0);
    expect(formatDateKey(date)).toBe('2024-10-04');
    expect(formatDateKeyCompact(date)).toBe('20241004');
  });

  it('ensures conversion from strings and Date instances', () => {
    const fromString = ensureDate('2024-05-20');
    const fromDate = ensureDate(new Date('2024-05-20T00:00:00Z'));

    expect(fromString).toBeInstanceOf(Date);
    expect(fromDate).toBeInstanceOf(Date);
  });

  it('adds Eastern days while accounting for DST transitions', () => {
    const beforeDstSwitch = createEasternDate(2024, 11, 3, 9, 30); // Daylight saving ends Nov 3 2024
    const nextTradingDay = addEasternDays(beforeDstSwitch, 1);
    expect(iso(nextTradingDay)).toBe('2024-11-04T14:30:00.000Z');
  });

  it('checks range membership using UTC timestamps', () => {
    const start = createEasternDate(2024, 7, 1, 0, 0);
    const end = createEasternDate(2024, 7, 1, 23, 59, 59, 999);
    const inside = createEasternDate(2024, 7, 1, 12, 0);
    const outside = createEasternDate(2024, 7, 2, 0, 0);

    expect(isWithinRange(inside, start, end)).toBe(true);
    expect(isWithinRange(outside, start, end)).toBe(false);
  });
});
