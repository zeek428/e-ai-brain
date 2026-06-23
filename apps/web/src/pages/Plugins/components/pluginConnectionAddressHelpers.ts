export function parseGitRepositoryAddress(value: unknown): { owner: string; repo: string } | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const sshMatch = trimmed.match(/^[^@\s]+@[^:\s]+:(.+)$/);
  let path = sshMatch?.[1] ?? trimmed;
  if (!sshMatch) {
    const firstSegment = trimmed.split('/')[0] ?? '';
    const looksLikeUrl = trimmed.includes('://') || firstSegment.includes('.');
    try {
      if (looksLikeUrl) {
        const url = new URL(trimmed.includes('://') ? trimmed : `https://${trimmed}`);
        path = url.pathname;
      }
    } catch {
      path = trimmed;
    }
  }
  const segments = path
    .replace(/^\/+/, '')
    .replace(/\/+$/, '')
    .split('/')
    .filter(Boolean);
  const repoSegments = segments[0] === 'repos' ? segments.slice(1) : segments;
  const owner = repoSegments[0]?.trim();
  const repo = repoSegments[1]?.replace(/\.git$/i, '').trim();
  return owner && repo ? { owner, repo } : undefined;
}

export function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function parseGitLabProjectAddress(
  value: unknown,
): { endpointUrl?: string; projectId: string; projectPath: string } | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const sshMatch = trimmed.match(/^[^@\s]+@([^:\s]+):(.+)$/);
  let endpointUrl: string | undefined;
  let path = sshMatch?.[2] ?? trimmed;
  if (sshMatch) {
    endpointUrl = `https://${sshMatch[1]}`;
  } else {
    const firstSegment = trimmed.split('/')[0] ?? '';
    const looksLikeUrl =
      trimmed.includes('://')
      || firstSegment.includes('.')
      || firstSegment.includes(':')
      || firstSegment === 'localhost';
    try {
      if (looksLikeUrl) {
        const url = new URL(trimmed.includes('://') ? trimmed : `http://${trimmed}`);
        endpointUrl = `${url.protocol}//${url.host}`;
        path = url.pathname;
      }
    } catch {
      path = trimmed;
    }
  }
  const normalizedPath = path.split('/-/', 1)[0] ?? path;
  let segments = normalizedPath
    .replace(/^\/+/, '')
    .replace(/\/+$/, '')
    .split('/')
    .filter(Boolean);
  if (segments.length >= 4 && segments[0] === 'api' && segments[2] === 'projects') {
    segments = [safeDecodeURIComponent(segments[3])];
  }
  const projectPath = safeDecodeURIComponent(segments.join('/')).replace(/\.git$/i, '').replace(/^\/+|\/+$/g, '');
  if (!projectPath || !projectPath.includes('/')) {
    return undefined;
  }
  return {
    endpointUrl,
    projectId: encodeURIComponent(projectPath),
    projectPath,
  };
}
