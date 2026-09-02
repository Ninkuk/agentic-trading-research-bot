import { act, renderHook } from "@testing-library/react";
import { useIsMobile } from "./useIsMobile";

function withWidth(width: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
}

afterEach(() => withWidth(1024));

test("a phone and a portrait tablet are mobile; a landscape tablet is not", () => {
  withWidth(390);
  expect(renderHook(() => useIsMobile()).result.current).toBe(true);
  withWidth(834);
  expect(renderHook(() => useIsMobile()).result.current).toBe(true);
  withWidth(1024);
  expect(renderHook(() => useIsMobile()).result.current).toBe(false);
});

test("the sidebar inset can shrink below its widest table (no page-level horizontal scroll)", async () => {
  const { render } = await import("@testing-library/react");
  const fixture = (await import("../fixtures/data.json")).default;
  const { AppShell } = await import("../ui/AppShell");
  render(
    <AppShell doc={fixture as never} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  const inset = document.querySelector('[data-slot="sidebar-inset"]') as HTMLElement;
  act(() => {});
  expect(inset.className).toContain("min-w-0");
});
