export function trimText(value?: string) {
  const trimmed = value?.trim();
  return trimmed || undefined;
}

export function splitCommaText(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value.map((item) => item.trim()).filter(Boolean);
  }
  return (value ?? '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinTextList(value?: string[]) {
  return value?.join(', ') ?? '';
}

export function formatMutationError(error: unknown) {
  if (error instanceof Error) {
    const detail = error as Error & { code?: string; traceId?: string };
    return [detail.code, error.message, detail.traceId ? `trace_id=${detail.traceId}` : undefined]
      .filter(Boolean)
      .join(' · ');
  }
  return '请求失败';
}
