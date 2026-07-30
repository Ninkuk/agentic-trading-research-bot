import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { MacroDrivers } from "./MacroDrivers";

const doc = fixture as unknown as DashboardDoc;

test("renders a tile caption and delta for every macro driver", () => {
  render(<MacroDrivers sec={doc.sections["macro-drivers"]} glossary={doc.glossary} />);
  expect(screen.getByText("10y–2y spread")).toBeInTheDocument(); // no band -> plain label caption
  expect(screen.getByText("VIX · calm")).toBeInTheDocument(); // band present -> "label · band"
  expect(screen.getByText("+0.02")).toBeInTheDocument(); // t10y2y delta
  expect(screen.getByText("−0.05")).toBeInTheDocument(); // hy spread delta
  expect(screen.getByText("−0.40")).toBeInTheDocument(); // vix delta
});
