import { DatePicker } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import type { CSSProperties, FocusEvent } from 'react';

dayjs.extend(customParseFormat);

const dateFormat = 'YYYY-MM-DD';
const dateTimeDisplayFormat = 'YYYY-MM-DD HH:mm:ss';
const dateTimeApiFormat = 'YYYY-MM-DDTHH:mm:ss[Z]';

type PickerMode = 'date' | 'dateTime';

type DateStringPickerProps = {
  allowClear?: boolean;
  disabled?: boolean;
  mode?: PickerMode;
  onBlur?: (event: FocusEvent<HTMLElement>) => void;
  onChange?: (value?: string) => void;
  placeholder?: string;
  style?: CSSProperties;
  value?: string;
};

function findValidDate(rawValue: string, formats: string[]) {
  for (const format of formats) {
    const parsed = dayjs(rawValue, format, true);
    if (parsed.isValid()) {
      return parsed;
    }
  }
  return undefined;
}

function normalizeDateOnly(rawValue?: string) {
  const trimmed = rawValue?.trim();
  if (!trimmed) {
    return undefined;
  }
  const parsed = findValidDate(trimmed, [dateFormat]) ?? dayjs(trimmed);
  return parsed.isValid() ? parsed.format(dateFormat) : trimmed;
}

function normalizeDateTime(rawValue?: string) {
  const trimmed = rawValue?.trim();
  if (!trimmed) {
    return undefined;
  }
  const normalized = trimmed
    .replace('T', ' ')
    .replace(/Z$/i, '')
    .replace(/\.\d+$/, '');
  const parsed =
    findValidDate(normalized, [dateTimeDisplayFormat, 'YYYY-MM-DD HH:mm', dateFormat]) ?? dayjs(trimmed);
  return parsed.isValid() ? parsed.format(dateTimeApiFormat) : trimmed;
}

function formatPickerValue(value: Dayjs | null, mode: PickerMode) {
  if (!value) {
    return undefined;
  }
  return mode === 'dateTime' ? value.format(dateTimeApiFormat) : value.format(dateFormat);
}

function parsePickerValue(value: string | undefined, mode: PickerMode) {
  const normalized = mode === 'dateTime' ? normalizeDateTime(value) : normalizeDateOnly(value);
  if (!normalized) {
    return undefined;
  }
  const rawValue =
    mode === 'dateTime'
      ? normalized.replace('T', ' ').replace(/Z$/i, '')
      : normalized;
  const parsed = dayjs(rawValue, mode === 'dateTime' ? dateTimeDisplayFormat : dateFormat, true);
  return parsed.isValid() ? parsed : undefined;
}

export function DateStringPicker({
  mode = 'date',
  onBlur,
  onChange,
  placeholder,
  style,
  value,
  ...restProps
}: DateStringPickerProps) {
  const handleBlur = (event: FocusEvent<HTMLElement>) => {
    const rawValue = 'value' in event.target ? String(event.target.value) : '';
    onChange?.(mode === 'dateTime' ? normalizeDateTime(rawValue) : normalizeDateOnly(rawValue));
    onBlur?.(event);
  };

  return (
    <DatePicker
      {...restProps}
      format={mode === 'dateTime' ? dateTimeDisplayFormat : dateFormat}
      onBlur={handleBlur}
      onChange={(date) => onChange?.(formatPickerValue(date as Dayjs | null, mode))}
      placeholder={placeholder ?? (mode === 'dateTime' ? '请选择时间' : '请选择日期')}
      showTime={mode === 'dateTime' ? { format: 'HH:mm:ss' } : undefined}
      style={{ width: '100%', ...style }}
      value={parsePickerValue(value, mode)}
    />
  );
}
