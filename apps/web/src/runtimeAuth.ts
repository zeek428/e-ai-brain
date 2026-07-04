import { getAccessToken, logout } from './services/aiBrain';
import { navigateTo } from './utils/navigation';

const PUBLIC_AUTH_PATHS = new Set(['/login', '/login/dingtalk/callback']);

function loginRedirectFor(pathname: string, search: string) {
  const target = `${pathname}${search}`;
  return `/login?redirect=${encodeURIComponent(target)}`;
}

export function redirectToLoginIfNeeded(
  pathname = window.location.pathname,
  search = window.location.search,
) {
  if (PUBLIC_AUTH_PATHS.has(pathname) || getAccessToken()) {
    return false;
  }
  navigateTo(loginRedirectFor(pathname, search));
  return true;
}

export async function handleLogout() {
  await logout();
  navigateTo('/login');
}
