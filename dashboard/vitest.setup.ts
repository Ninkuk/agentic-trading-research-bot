import "@testing-library/jest-dom/vitest";

class Stub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// jsdom has neither; StrandNav (IntersectionObserver) and any chart sizing
// (ResizeObserver) would throw ReferenceError in every render test.
(globalThis as any).IntersectionObserver ??= Stub;
(globalThis as any).ResizeObserver ??= Stub;

// jsdom has no matchMedia either; useIsMobile (sidebar) queries it on
// mount. Always "desktop" here — the mobile sheet is a browser concern.
(globalThis as any).matchMedia ??= (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addEventListener() {},
  removeEventListener() {},
  addListener() {},
  removeListener() {},
  dispatchEvent() {
    return false;
  },
});
// jsdom's window.scrollTo logs "Not implemented"; Main scrolls to top on
// every strand switch.
window.scrollTo = () => {};
