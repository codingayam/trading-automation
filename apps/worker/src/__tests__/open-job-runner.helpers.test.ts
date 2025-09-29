import { describe, expect, it } from 'vitest';

import {
  collectDatesForWindow,
  normalizeMemberName,
  normalizeParty,
  normalizeTransaction,
  toUpperTicker,
} from '../open-job-runner.js';
import { createEasternDate, formatDateKey } from '@trading-automation/shared';

describe('open-job-runner helpers', () => {
  describe('toUpperTicker', () => {
    it('returns upper-cased tickers when value is present', () => {
      expect(toUpperTicker(' aapl ')).toBe('AAPL');
    });

    it('returns null when value is empty', () => {
      expect(toUpperTicker('   ')).toBeNull();
      expect(toUpperTicker(null)).toBeNull();
    });
  });

  describe('normalizeMemberName', () => {
    it('trims whitespace and keeps non-empty names', () => {
      expect(normalizeMemberName('  Doe ')).toBe('Doe');
    });

    it('returns null for blank inputs', () => {
      expect(normalizeMemberName('   ')).toBeNull();
      expect(normalizeMemberName(undefined)).toBeNull();
    });
  });

  describe('normalizeTransaction', () => {
    it('maps purchase synonyms to BUY', () => {
      expect(normalizeTransaction('Purchase of securities')).toBe('BUY');
      expect(normalizeTransaction(' buy ')).toBe('BUY');
    });

    it('maps sale synonyms to SELL', () => {
      expect(normalizeTransaction('Sale of stock')).toBe('SELL');
      expect(normalizeTransaction('sold')).toBe('UNKNOWN');
    });

    it('returns UNKNOWN for other values', () => {
      expect(normalizeTransaction('hold')).toBe('UNKNOWN');
      expect(normalizeTransaction(null)).toBe('UNKNOWN');
    });
  });

  describe('normalizeParty', () => {
    it('normalizes party abbreviations', () => {
      expect(normalizeParty('d')).toBe('DEMOCRAT');
      expect(normalizeParty(' REP ')).toBe('REPUBLICAN');
      expect(normalizeParty('ind')).toBe('INDEPENDENT');
      expect(normalizeParty('other')).toBe('OTHER');
    });

    it('returns UNKNOWN for unrecognized values', () => {
      expect(normalizeParty('libertarian')).toBe('UNKNOWN');
    });

    it('handles empty or whitespace inputs', () => {
      expect(normalizeParty('   ')).toBe('UNKNOWN');
      expect(normalizeParty(undefined)).toBeNull();
    });
  });

  describe('collectDatesForWindow', () => {
    const start = createEasternDate(2025, 9, 24, 12, 0, 0);
    const end = createEasternDate(2025, 9, 25, 8, 0, 0);

    it('returns inclusive eastern days spanning the window', () => {
      const dates = collectDatesForWindow({ label: 'current', start, end });
      expect(dates.map((date) => formatDateKey(date))).toEqual(['2025-09-24', '2025-09-25']);
    });

    it('returns a single day when start and end overlap', () => {
      const dates = collectDatesForWindow({ label: 'previous', start, end: start });
      expect(dates.map((date) => formatDateKey(date))).toEqual(['2025-09-24']);
    });
  });
});
