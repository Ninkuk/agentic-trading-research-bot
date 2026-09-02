import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc, Section } from "../types";
import { YieldCurve } from "./YieldCurve";

const doc = fixture as unknown as DashboardDoc;

const LIVE: Section = {
  title: "Treasury yield curve",
  kicker: "Sources",
  tiles: [
    { label: "3-month", value: 3.85, band: "2026-08-26", tone: null },
    { label: "2-year", value: 4.19, band: "2026-08-26", tone: null },
    { label: "10-year", value: 4.66, band: "2026-08-26", tone: null },
    { label: "10y − 2y spread", value: 0.47, band: "normal", tone: "on" },
    { label: "10y − 3m spread", value: 0.81, band: null, tone: "on" },
  ],
};

test("maturity tiles become one line over an ordinal 3m/2y/10y axis; spreads stay tiles", () => {
  const { container } = render(<YieldCurve sec={LIVE} glossary={doc.glossary} />);
  const curve = container.querySelector(".yield-curve-line .recharts-line-curve");
  expect(curve).toHaveAttribute("stroke", "var(--color-yield)");
  expect(curve).toHaveAttribute("stroke-width", "2");
  expect(container.querySelectorAll(".recharts-line-dot")).toHaveLength(3);
  // recharts 3 renders tick labels outside the axis group; the ordinal
  // labels appear in maturity order before the numeric y ticks.
  const labels = [...container.querySelectorAll("svg text")].map((t) => t.textContent);
  expect(labels.slice(0, 3)).toEqual(["3m", "2y", "10y"]);
  // Spreads render as tiles with their tone; maturities do not repeat as tiles.
  expect(screen.getByText("0.47")).toHaveClass("tag-on");
  expect(screen.getByText("10y − 3m spread")).toBeInTheDocument();
  expect(screen.queryByText("3-month · 2026-08-26")).toBeNull();
});

test("fewer than two numeric maturities renders the tiles only", () => {
  const sec: Section = {
    tiles: [
      { label: "10-year", value: 4.66 },
      { label: "2-year", value: null },
      { label: "10y − 2y spread", value: 0.47, tone: "on" },
    ],
  };
  const { container } = render(<YieldCurve sec={sec} glossary={doc.glossary} />);
  expect(container.querySelector("svg")).toBeNull();
  expect(screen.getByText("10-year")).toBeInTheDocument();
  expect(screen.getByText("10y − 2y spread")).toBeInTheDocument();
});
