import '@testing-library/jest-dom/vitest';

const originalGetComputedStyle = window.getComputedStyle.bind(window);

Object.defineProperty(window, 'getComputedStyle', {
  value: (element: Element) => originalGetComputedStyle(element),
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
});

class TestResizeObserver {
  observe() {
    return undefined;
  }

  unobserve() {
    return undefined;
  }

  disconnect() {
    return undefined;
  }
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: TestResizeObserver,
});

Object.defineProperty(globalThis, 'ResizeObserver', {
  writable: true,
  value: TestResizeObserver,
});
