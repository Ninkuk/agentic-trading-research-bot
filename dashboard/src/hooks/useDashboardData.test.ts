import { renderHook, waitFor } from "@testing-library/react";
import type { DashboardDoc } from "../types";
import { useDashboardData } from "./useDashboardData";

const DOC: DashboardDoc = {
  schema_version: 1,
  generated_at: "2026-07-29T00:00:00+00:00",
  edition_date: "July 28, 2026",
  snapshot_number: 1,
  hero: { bullets: [] },
  sections: {},
  tickers: {},
  glossary: {},
};

afterEach(() => {
  vi.unstubAllGlobals();
});

test("loads the document successfully", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => DOC }),
  );
  const { result } = renderHook(() => useDashboardData());
  await waitFor(() => expect(result.current.doc).toBeDefined());
  expect(result.current.doc?.schema_version).toBe(1);
  expect(result.current.error).toBeUndefined();
});

test("surfaces a fetch failure as an error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
  const { result } = renderHook(() => useDashboardData());
  await waitFor(() => expect(result.current.error).toBeDefined());
  expect(result.current.error).toMatch(/network down/);
  expect(result.current.doc).toBeUndefined();
});

test("surfaces a top-level error document without treating it as data", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ error: "sqlite locked" }) }),
  );
  const { result } = renderHook(() => useDashboardData());
  await waitFor(() => expect(result.current.error).toBeDefined());
  expect(result.current.error).toBe("sqlite locked");
  expect(result.current.doc).toBeUndefined();
});

test("flags stale when generated_at is more than 36h behind the client clock", async () => {
  const oldIso = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...DOC, generated_at: oldIso }) }),
  );
  const { result } = renderHook(() => useDashboardData());
  await waitFor(() => expect(result.current.doc).toBeDefined());
  expect(result.current.stale).toBe(true);
});

test("is not stale when generated_at is recent", async () => {
  const recentIso = new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...DOC, generated_at: recentIso }) }),
  );
  const { result } = renderHook(() => useDashboardData());
  await waitFor(() => expect(result.current.doc).toBeDefined());
  expect(result.current.stale).toBe(false);
});
