export function compactJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

export function connectionTestStatusColor(status: string) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  return 'default';
}

export function runnerHealthStatusColor(status: string | undefined) {
  if (status === 'managed') {
    return 'blue';
  }
  if (status === 'online') {
    return 'green';
  }
  if (status === 'offline') {
    return 'orange';
  }
  if (status === 'never_connected') {
    return 'default';
  }
  if (status === 'disabled') {
    return 'red';
  }
  return 'blue';
}
