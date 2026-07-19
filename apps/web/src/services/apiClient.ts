function defaultDevelopmentApiBaseUrl() {
  if (process.env.NODE_ENV !== 'development') {
    return '';
  }
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }
  // Browser requests stay same-origin in development so the checked-in Umi
  // `/api` proxy owns the API connection. This also avoids a separate CORS
  // dependency for localhost and private-network development hosts.
  return '';
}

const defaultApiBaseUrl = defaultDevelopmentApiBaseUrl();
const configuredApiBaseUrl = process.env.UMI_APP_API_BASE_URL ?? defaultApiBaseUrl;

export const API_BASE_URL = configuredApiBaseUrl.endsWith('/')
  ? configuredApiBaseUrl.slice(0, -1)
  : configuredApiBaseUrl;

export type ApiEnvelope<T> = {
  data: T;
};

export type ApiErrorPayload = {
  detail?: {
    code?: string;
    message?: string;
    trace_id?: string;
    [key: string]: unknown;
  };
};

export type RemoteListPerformance = {
  duration_ms?: number;
  p95_target_ms?: number;
  result_count?: number;
  slow?: boolean;
  slow_threshold_ms?: number;
  total?: number;
};

export type RemoteListQueryEcho = {
  filters?: Record<string, unknown>;
  name?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
};

export type ListResponse<T> = {
  items: T[];
  limit?: number;
  next_cursor?: string | null;
  page?: number;
  page_size?: number;
  performance?: RemoteListPerformance;
  query?: RemoteListQueryEcho;
  total: number;
};

type RemoteListQueryParams = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: string;
};

type UnauthorizedApiResponseHandler = () => void;
type ForbiddenApiResponseHandler = (error: ApiRequestError, path: string) => boolean;

let unauthorizedApiResponseHandler: UnauthorizedApiResponseHandler | undefined;
let forbiddenApiResponseHandler: ForbiddenApiResponseHandler | undefined;

export function setUnauthorizedApiResponseHandler(
  handler: UnauthorizedApiResponseHandler | undefined,
) {
  unauthorizedApiResponseHandler = handler;
}

export function setForbiddenApiResponseHandler(
  handler: ForbiddenApiResponseHandler | undefined,
) {
  forbiddenApiResponseHandler = handler;
}

export class ApiRequestError extends Error {
  authorizationRefreshHandled?: boolean;
  code?: string;
  detail?: ApiErrorPayload['detail'];
  status: number;
  traceId?: string;

  constructor({
    code,
    detail,
    message,
    status,
    traceId,
  }: {
    code?: string;
    detail?: ApiErrorPayload['detail'];
    message: string;
    status: number;
    traceId?: string;
  }) {
    super(message);
    this.name = 'ApiRequestError';
    this.code = code;
    this.detail = detail;
    this.status = status;
    this.traceId = traceId;
  }
}

export async function apiRequest<T>(
  path: string,
  options: {
    method?: string;
    token?: string;
    body?: unknown;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: options.body ? JSON.stringify(options.body) : undefined,
    headers: {
      'Content-Type': 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    method: options.method ?? 'GET',
    signal: options.signal,
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const requestError = new ApiRequestError({
      code: payload?.detail?.code,
      detail: payload?.detail,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
    if (response.status === 401 && shouldHandleUnauthorizedResponse(path)) {
      unauthorizedApiResponseHandler?.();
    }
    if (
      response.status === 403 &&
      requestError.code === 'FORBIDDEN' &&
      shouldHandleForbiddenResponse(path)
    ) {
      requestError.authorizationRefreshHandled =
        forbiddenApiResponseHandler?.(requestError, path) === true;
    }
    throw requestError;
  }
  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}

export async function apiFormRequest<T>(
  path: string,
  options: {
    method?: string;
    token?: string;
    body: FormData;
    signal?: AbortSignal;
  },
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: options.body,
    headers: {
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    method: options.method ?? 'POST',
    signal: options.signal,
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const requestError = new ApiRequestError({
      code: payload?.detail?.code,
      detail: payload?.detail,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
    if (response.status === 401 && shouldHandleUnauthorizedResponse(path)) {
      unauthorizedApiResponseHandler?.();
    }
    if (
      response.status === 403 &&
      requestError.code === 'FORBIDDEN' &&
      shouldHandleForbiddenResponse(path)
    ) {
      requestError.authorizationRefreshHandled =
        forbiddenApiResponseHandler?.(requestError, path) === true;
    }
    throw requestError;
  }
  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}

function shouldHandleUnauthorizedResponse(path: string) {
  return !(
    path.startsWith('/api/auth/login') ||
    path.startsWith('/api/auth/dingtalk/exchange-ticket') ||
    path.startsWith('/api/auth/providers')
  );
}

function shouldHandleForbiddenResponse(path: string) {
  return !(
    path.startsWith('/api/auth/me') ||
    path.startsWith('/api/auth/login') ||
    path.startsWith('/api/auth/dingtalk/exchange-ticket') ||
    path.startsWith('/api/auth/providers')
  );
}

export function appendQueryParam(
  params: URLSearchParams,
  key: string,
  value?: boolean | number | string,
) {
  if (value === undefined || value === null || value === '') {
    return;
  }
  params.set(key, String(value));
}

export function appendRemoteListParams(params: URLSearchParams, query: RemoteListQueryParams) {
  appendQueryParam(params, 'page', query.page ?? 1);
  appendQueryParam(params, 'page_size', query.pageSize ?? 10);
  appendQueryParam(params, 'sort_by', query.sortField);
  appendQueryParam(
    params,
    'sort_order',
    query.sortOrder === 'ascend' ? 'asc' : query.sortOrder === 'descend' ? 'desc' : undefined,
  );
}
