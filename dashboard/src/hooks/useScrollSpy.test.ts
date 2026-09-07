import { act, renderHook } from "@testing-library/react";
import { useScrollSpy } from "./useScrollSpy";

type Callback = (
  records: { target: { id: string }; isIntersecting: boolean }[],
) => void;

let callback: Callback | null = null;
const observed: string[] = [];
const disconnect = vi.fn();

class FakeObserver {
  constructor(cb: Callback) {
    callback = cb;
  }
  observe(el: Element) {
    observed.push(el.id);
  }
  disconnect() {
    disconnect();
  }
}

beforeEach(() => {
  callback = null;
  observed.length = 0;
  disconnect.mockClear();
  vi.stubGlobal("IntersectionObserver", FakeObserver);
  document.body.innerHTML =
    '<section id="a"></section><section id="b"></section><section id="c"></section>';
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

test("reports the first visible id in DOM order, and null when none is", () => {
  const { result, unmount } = renderHook(() => useScrollSpy(["a", "b", "c"]));
  expect(result.current).toBeNull();
  expect(observed).toEqual(["a", "b", "c"]);
  act(() =>
    callback?.([
      { target: { id: "c" }, isIntersecting: true },
      { target: { id: "b" }, isIntersecting: true },
    ]),
  );
  expect(result.current).toBe("b");
  act(() => callback?.([{ target: { id: "b" }, isIntersecting: false }]));
  expect(result.current).toBe("c");
  act(() => callback?.([{ target: { id: "c" }, isIntersecting: false }]));
  expect(result.current).toBeNull();
  unmount();
  expect(disconnect).toHaveBeenCalled();
});

test("an id with no element is skipped, not an error", () => {
  const { result } = renderHook(() => useScrollSpy(["a", "missing"]));
  expect(observed).toEqual(["a"]);
  expect(result.current).toBeNull();
});
