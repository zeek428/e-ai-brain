export const DEFAULT_DISPLAY_TIME_ZONE = 'Asia/Shanghai';

function fallbackDateText(value: string) {
  return value
    .replace('T', ' ')
    .replace(/\.\d+/, '')
    .replace(/Z$/i, '')
    .replace(/[+-]\d{2}:?\d{2}$/, '')
    .slice(0, 16);
}

function formatDateTimeInDisplayTimeZone(date: Date) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    day: '2-digit',
    hour: '2-digit',
    hourCycle: 'h23',
    minute: '2-digit',
    month: '2-digit',
    timeZone: DEFAULT_DISPLAY_TIME_ZONE,
    year: 'numeric',
  }).formatToParts(date);
  const valueByType = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${valueByType.year}-${valueByType.month}-${valueByType.day} ${valueByType.hour}:${valueByType.minute}`;
}

export function formatDisplayDateTime(value?: Date | number | string | null) {
  if (value === undefined || value === null) {
    return '-';
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? '-' : formatDateTimeInDisplayTimeZone(value);
  }
  const trimmed = String(value).trim();
  if (!trimmed || trimmed === '-') {
    return '-';
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return trimmed;
  }
  const normalized = trimmed.replace(' ', 'T').replace(/\.(\d{3})\d+/, '.$1');
  if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(normalized)) {
    return fallbackDateText(trimmed);
  }
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    return fallbackDateText(trimmed);
  }
  return formatDateTimeInDisplayTimeZone(parsed);
}

export function formatDisplayDate(value?: Date | number | string | null) {
  const formatted = formatDisplayDateTime(value);
  return formatted === '-' ? undefined : formatted.slice(0, 10);
}
