import { render, screen } from "@testing-library/react";
import type { Section } from "../types";
import { SectionShell } from "./SectionShell";

const sec: Section = {
  title: "Regime",
  kicker: "Macro",
  note: "The market's mood.",
  verdict: { text: "Risk-on", tone: "on" },
  caveat: "Trust lightly.",
};

beforeEach(() => {
  localStorage.clear();
});

test("renders title, verdict, note, caveat and children — but not the kicker (the strand heading already labels the group)", () => {
  render(
    <SectionShell id="regime" sec={sec}>
      <div>body content</div>
    </SectionShell>,
  );
  expect(screen.queryByText("Macro")).not.toBeInTheDocument();
  expect(screen.getByText("Regime")).toBeInTheDocument();
  expect(screen.getByText("Risk-on")).toBeInTheDocument();
  expect(screen.getByText("The market's mood.")).toBeInTheDocument();
  expect(screen.getByText("body content")).toBeInTheDocument();
  expect(screen.getByText("Trust lightly.")).toBeInTheDocument();
});

test("renders an error state inside the shell instead of children", () => {
  const errSec: Section = { title: "Candidates", error: "unavailable (stocks.db: OperationalError)" };
  render(
    <SectionShell id="candidates" sec={errSec}>
      <div>should not show</div>
    </SectionShell>,
  );
  expect(screen.getByText("unavailable (stocks.db: OperationalError)")).toBeInTheDocument();
  expect(screen.queryByText("should not show")).not.toBeInTheDocument();
});

test("renders an empty state when rows are empty and an empty message is set", () => {
  const emptySec: Section = {
    title: "Bucket performance",
    rows: [],
    empty: "no matured buckets yet",
  };
  render(<SectionShell id="bucket-performance" sec={emptySec} />);
  expect(screen.getByText("no matured buckets yet")).toBeInTheDocument();
});
