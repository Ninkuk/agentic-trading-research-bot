import { render } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { RegimeTimelineSection } from "./RegimeTimelineSection";

const doc = fixture as unknown as DashboardDoc;

test("renders one strip cell per fixture row", () => {
  const { container } = render(
    <RegimeTimelineSection sec={doc.sections["regime-timeline"]} glossary={doc.glossary} />,
  );
  const cells = container.querySelectorAll(".strip-cell");
  expect(cells.length).toBe(doc.sections["regime-timeline"].rows?.length ?? 0);
  expect(cells.length).toBeGreaterThanOrEqual(4);
});
