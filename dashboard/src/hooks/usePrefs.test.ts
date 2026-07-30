import { act, renderHook } from "@testing-library/react";
import { usePrefs } from "./usePrefs";

beforeEach(() => {
  localStorage.clear();
});

test("reads the initial value when nothing is stored", () => {
  const { result } = renderHook(() => usePrefs("k1", 5));
  expect(result.current[0]).toBe(5);
});

test("persists updates to localStorage under the atrb: prefix, JSON serialized", () => {
  const { result } = renderHook(() => usePrefs("k2", { a: 1 }));
  act(() => result.current[1]({ a: 2 }));
  expect(result.current[0]).toEqual({ a: 2 });
  expect(localStorage.getItem("atrb:k2")).toBe(JSON.stringify({ a: 2 }));
});

test("reads a persisted value back on mount", () => {
  localStorage.setItem("atrb:k3", JSON.stringify(42));
  const { result } = renderHook(() => usePrefs("k3", 0));
  expect(result.current[0]).toBe(42);
});

test("falls back to state-only when storage throws (private mode)", () => {
  const original = Storage.prototype.setItem;
  Storage.prototype.setItem = () => {
    throw new Error("quota exceeded");
  };
  try {
    const { result } = renderHook(() => usePrefs("k4", 1));
    act(() => result.current[1](2));
    expect(result.current[0]).toBe(2);
  } finally {
    Storage.prototype.setItem = original;
  }
});
