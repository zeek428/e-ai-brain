import { navigateTo } from '../utils/navigation';
import {
  ApiRequestError,
  apiRequest,
  setUnauthorizedApiResponseHandler,
} from './apiClient';

const ACCESS_TOKEN_STORAGE_KEY = 'ai_brain_access_token';
const CURRENT_USER_STORAGE_KEY = 'ai_brain_current_user';

export const AUTH_STATE_EVENT = 'ai-brain-auth-state-changed';

export type MenuTreeNode = {
  children?: MenuTreeNode[];
  code: string;
  name: string;
  path?: string | null;
};

export type ScopeGrant = {
  access_level: string;
  scope_id: string;
  scope_name?: string;
  scope_type: string;
};

export type CurrentUserResponse = {
  display_name: string;
  id: string;
  menu_tree?: MenuTreeNode[];
  permissions?: string[];
  route_permissions?: Record<string, string[]>;
  roles: string[];
  scope_summary?: ScopeGrant[];
  username: string;
};

export type LoginResponse = {
  access_token: string;
  user: CurrentUserResponse;
};

type AuthLocalCacheClearHandler = () => void;

let authLocalCacheClearHandler: AuthLocalCacheClearHandler | undefined;

export function setAuthLocalCacheClearHandler(handler: AuthLocalCacheClearHandler | undefined) {
  authLocalCacheClearHandler = handler;
}

function emitAuthStateChanged() {
  if (typeof globalThis.dispatchEvent !== 'function' || typeof Event !== 'function') {
    return;
  }
  globalThis.dispatchEvent(new Event(AUTH_STATE_EVENT));
}

export function getAccessToken() {
  const storedToken =
    typeof globalThis.localStorage === 'undefined'
      ? undefined
      : globalThis.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  return storedToken || process.env.UMI_APP_API_TOKEN || undefined;
}

export function requireAccessToken() {
  const token = getAccessToken();
  if (!token) {
    throw new ApiRequestError({
      code: 'AUTH_REQUIRED',
      message: '缺少访问令牌，请先登录后再加载真实数据。',
      status: 401,
    });
  }
  return token;
}

export function saveAccessToken(token: string) {
  if (typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function saveCurrentUser(user: CurrentUserResponse) {
  if (!user || typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.setItem(CURRENT_USER_STORAGE_KEY, JSON.stringify(user));
  emitAuthStateChanged();
}

export function getStoredCurrentUser(): CurrentUserResponse | undefined {
  if (typeof globalThis.localStorage === 'undefined') {
    return undefined;
  }
  const value = globalThis.localStorage.getItem(CURRENT_USER_STORAGE_KEY);
  if (!value) {
    return undefined;
  }
  try {
    return JSON.parse(value) as CurrentUserResponse;
  } catch {
    globalThis.localStorage.removeItem(CURRENT_USER_STORAGE_KEY);
    return undefined;
  }
}

export function clearAccessToken() {
  if (typeof globalThis.localStorage === 'undefined') {
    return;
  }
  authLocalCacheClearHandler?.();
  globalThis.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  globalThis.localStorage.removeItem(CURRENT_USER_STORAGE_KEY);
  emitAuthStateChanged();
}

export function handleUnauthorizedApiResponse() {
  clearAccessToken();
  if (typeof window === 'undefined') {
    return;
  }
  const { pathname, search } = window.location;
  if (pathname === '/login') {
    return;
  }
  const target = `${pathname}${search}`;
  navigateTo(`/login?redirect=${encodeURIComponent(target)}`);
}

setUnauthorizedApiResponseHandler(handleUnauthorizedApiResponse);

export async function login(username: string, password: string): Promise<LoginResponse> {
  const loginResponse = await apiRequest<LoginResponse>('/api/auth/login', {
    body: { username, password },
    method: 'POST',
  });
  saveAccessToken(loginResponse.access_token);
  saveCurrentUser(loginResponse.user);
  return loginResponse;
}

export async function fetchCurrentUser(): Promise<CurrentUserResponse> {
  const token = requireAccessToken();
  const user = await apiRequest<CurrentUserResponse>('/api/auth/me', { token });
  saveCurrentUser(user);
  return user;
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  clearAccessToken();
  if (!token) {
    return;
  }
  try {
    await apiRequest<{ success: boolean }>('/api/auth/logout', {
      method: 'POST',
      token,
    });
  } catch {
    // Local logout should still complete if the server token is already expired.
  }
}
