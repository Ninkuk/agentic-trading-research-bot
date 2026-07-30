import { render } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { RegimeTimelineSection } from "./RegimeTimelineSection";

const doc = fixture as unknown as DashboardDoc;

test("renders one regime-colored dot per fixture row with a VIX value", () => {
  const { container } = render(
    <RegimeTimelineSection sec={doc.sections["regime-timeline"]} glossary={doc.glossary} />,
  );
  // The strip layer was retired in the 2026-07 redesign — the per-night
  // regime read lives on the area chart's dots now.
  const dots = container.querySelectorAll(".regime-dot");
  const vixRows = (doc.sections["regime-timeline"].rows ?? []).filter((r) => r.vix !== null);
  expect(dots.length).toBe(vixRows.length);
  expect(dots.length).toBeGreaterThanOrEqual(4);
});
