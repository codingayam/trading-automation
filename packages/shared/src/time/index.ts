const EASTERN_TIME_ZONE = 'America/New_York';

export interface EasternDateParts {
  year: number;
  month: number; // 1-12
  day: number; // 1-31
  hour: number; // 0-23
  minute: number; // 0-59
  second: number; // 0-59
  millisecond?: number; // 0-999
}

const createDateTimeFormatter = () =>
  new Intl.DateTimeFormat('en-US', {
    timeZone: EASTERN_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

const createOffsetFormatter = () =>
  new Intl.DateTimeFormat('en-US', {
    timeZone: EASTERN_TIME_ZONE,
    timeZoneName: 'shortOffset',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

const DATE_TIME_FORMATTER = createDateTimeFormatter();
const OFFSET_FORMATTER = createOffsetFormatter();

const parseFormatterParts = (date: Date) => {
  const parts = DATE_TIME_FORMATTER.formatToParts(date);
  const result: Record<string, number> = {};

  for (const part of parts) {
    if (part.type === 'year' || part.type === 'month' || part.type === 'day' || part.type === 'hour' || part.type === 'minute' || part.type === 'second') {
      result[part.type] = Number(part.value);
    }
  }

  return {
    year: result.year,
    month: result.month,
    day: result.day,
    hour: result.hour,
    minute: result.minute,
    second: result.second,
  } as EasternDateParts;
};

const parseOffsetMinutes = (date: Date): number => {
  const parts = OFFSET_FORMATTER.formatToParts(date);
  const timeZonePart = parts.find((part) => part.type === 'timeZoneName');
  const match = timeZonePart?.value.match(/GMT([+-])(\d{1,2})(?::(\d{2}))?/);

  if (!match) {
    return 0;
  }

  const [sign, hours, minutes] = [match[1], match[2], match[3] ?? '0'];
  const signMultiplier = sign === '-' ? -1 : 1;
  const totalMinutes = Number(hours) * 60 + Number(minutes);

  return signMultiplier * totalMinutes;
};

const buildEasternDate = ({ year, month, day, hour, minute, second, millisecond = 0 }: EasternDateParts): Date => {
  const baseUtc = Date.UTC(year, month - 1, day, hour, minute, second, millisecond);
  const offsetMinutes = parseOffsetMinutes(new Date(baseUtc));
  const correctedUtc = baseUtc - offsetMinutes * 60_000;
  return new Date(correctedUtc);
};

export const toEasternDateParts = (date: Date): EasternDateParts => parseFormatterParts(date);

export const startOfEasternDay = (input: Date): Date => {
  const parts = toEasternDateParts(input);
  return buildEasternDate({ ...parts, hour: 0, minute: 0, second: 0, millisecond: 0 });
};

export const endOfEasternDay = (input: Date): Date => {
  const parts = toEasternDateParts(input);
  return buildEasternDate({ ...parts, hour: 23, minute: 59, second: 59, millisecond: 999 });
};

export const createEasternDate = (year: number, month: number, day: number, hour = 0, minute = 0, second = 0, millisecond = 0): Date =>
  buildEasternDate({ year, month, day, hour, minute, second, millisecond });

export const extractEasternDateOnly = (input: Date): Date => {
  const parts = toEasternDateParts(input);
  return buildEasternDate({ year: parts.year, month: parts.month, day: parts.day, hour: 0, minute: 0, second: 0, millisecond: 0 });
};

export const formatDateKey = (input: Date): string => {
  const parts = toEasternDateParts(input);
  const month = String(parts.month).padStart(2, '0');
  const day = String(parts.day).padStart(2, '0');
  return `${parts.year}-${month}-${day}`;
};

export const formatDateKeyCompact = (input: Date): string => {
  const parts = toEasternDateParts(input);
  const month = String(parts.month).padStart(2, '0');
  const day = String(parts.day).padStart(2, '0');
  return `${parts.year}${month}${day}`;
};

export const parseQuiverDate = (value: string | null | undefined): Date | null => {
  if (!value) {
    return null;
  }

  const trimmed = value.trim();

  if (!trimmed) {
    return null;
  }

  const dateMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);

  if (dateMatch) {
    const [, year, month, day] = dateMatch;
    return createEasternDate(Number(year), Number(month), Number(day));
  }

  const isoParsed = Number.isNaN(Date.parse(trimmed)) ? null : new Date(trimmed);

  if (isoParsed && !Number.isNaN(isoParsed.getTime())) {
    return isoParsed;
  }

  return null;
};

export const ensureDate = (value: Date | string): Date => {
  if (value instanceof Date) {
    return value;
  }

  const parsed = parseQuiverDate(value);

  if (!parsed) {
    throw new Error(`Unable to parse date string: ${value}`);
  }

  return parsed;
};

export const isWithinRange = (date: Date, rangeStart: Date, rangeEnd: Date): boolean => {
  const time = date.getTime();
  return time >= rangeStart.getTime() && time <= rangeEnd.getTime();
};

export const clampToRange = (date: Date, rangeStart: Date, rangeEnd: Date): Date => {
  if (date < rangeStart) {
    return new Date(rangeStart.getTime());
  }
  if (date > rangeEnd) {
    return new Date(rangeEnd.getTime());
  }
  return new Date(date.getTime());
};

export { EASTERN_TIME_ZONE };

export const addEasternDays = (input: Date, amount: number): Date => {
  const parts = toEasternDateParts(input);
  const base = createEasternDate(
    parts.year,
    parts.month,
    parts.day,
    parts.hour,
    parts.minute,
    parts.second,
    parts.millisecond ?? 0,
  );

  base.setUTCDate(base.getUTCDate() + amount);
  return base;
};
