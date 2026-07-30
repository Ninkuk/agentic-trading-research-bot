import { act, renderHook } from "@testing-library/react";
import { useHashRoute } from "./useHashRoute";

afterEach(() => {
  location.hash = "";
});

test("parses ticker route and reacts to hashchange", () => {
  location.hash = "#/ticker/DECK";
  const { result } = renderHook(() => useHashRoute());
  expect(result.current).toEqual({ route: "ticker", symbol: "DECK" });
  act(() => {
    location.hash = "#/";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(result.current).toEqual({ route: "main" });
});

test("parses main route when the hash is empty", () => {
  location.hash = "";
  const { result } = renderHook(() => useHashRoute());
  expect(result.current).toEqual({ route: "main" });
});
