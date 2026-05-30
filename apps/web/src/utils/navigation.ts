export function navigateTo(path: string) {
  window.history.pushState({}, '', path);
  const event =
    typeof PopStateEvent === 'function'
      ? new PopStateEvent('popstate', { state: null })
      : new Event('popstate');
  window.dispatchEvent(event);
}
