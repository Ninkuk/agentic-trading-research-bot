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
