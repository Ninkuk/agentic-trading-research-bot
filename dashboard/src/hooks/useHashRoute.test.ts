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

test("parses a strand route from a slash-prefixed slug", () => {
  location.hash = "#/track-record";
  const { result } = renderHook(() => useHashRoute());
  expect(result.current).toEqual({ route: "strand", id: "track-record" });
});

test("parses a bare section anchor (no slash) as a section route", () => {
  location.hash = "#scorecard";
  const { result } = renderHook(() => useHashRoute());
  expect(result.current).toEqual({ route: "section", id: "scorecard" });
});

test("a bare hash or trailing-slash strand slug still resolves", () => {
  location.hash = "#";
  expect(renderHook(() => useHashRoute()).result.current).toEqual({ route: "main" });
  location.hash = "#/macro/";
  expect(renderHook(() => useHashRoute()).result.current).toEqual({ route: "strand", id: "macro" });
});
