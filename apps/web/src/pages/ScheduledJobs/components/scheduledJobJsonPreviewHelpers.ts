export function isEmptyJsonValue(value: unknown): boolean {
  return (
    value == null
    || (Array.isArray(value) && value.length === 0)
    || (typeof value === 'object'
      && !Array.isArray(value)
      && Object.keys(value as Record<string, unknown>).length === 0)
  );
}

export function formatJsonValue(value: unknown): string {
  if (isEmptyJsonValue(value)) {
    return '暂无数据';
  }
  return JSON.stringify(value, null, 2);
}
