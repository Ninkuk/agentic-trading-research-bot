import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { SignalEfficacy } from "./SignalEfficacy";

const doc = fixture as unknown as DashboardDoc;

test("renders the recommendation as text-in-pill, one pill per known value", () => {
  render(<SignalEfficacy sec={doc.sections["signal-efficacy"]} glossary={doc.glossary} />);
  const keepPill = screen.getByText("keep");
  expect(keepPill).toHaveClass("pill", "keep");
  const watchPill = screen.getByText("watch");
  expect(watchPill).toHaveClass("pill", "watch");
});

test("renders the hit-rate dot plot's point estimate for a row", () => {
  render(<SignalEfficacy sec={doc.sections["signal-efficacy"]} glossary={doc.glossary} />);
  // si_spike's hit_rate is 0.58 -> EfficacyDotPlot's 0-dp "58%" readout.
  expect(screen.getByText("58%")).toBeInTheDocument();
});
