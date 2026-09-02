import { render, screen } from "@testing-library/react";
import { Masthead } from "./Masthead";

test("renders edition date and snapshot number", () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={42} />);
  expect(screen.getByText("July 28, 2026")).toBeInTheDocument();
  expect(screen.getByText("#42")).toBeInTheDocument();
});

test("omits the snapshot line when snapshotNumber is null", () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={null} />);
  expect(screen.queryByText(/^#/)).not.toBeInTheDocument();
});

test("deliberately carries no ticker search box", () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={1} />);
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});

test("on narrow screens the meta row spans full width, text left-aligned, toggle at the right", () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={42} />);
  const meta = screen.getByText("#42").closest(".mast-meta") as HTMLElement;
  // Full-width, space-between below sm; hugs the right edge from sm up.
  expect(meta.className).toMatch(/\bw-full\b/);
  expect(meta.className).toMatch(/\bjustify-between\b/);
  expect(meta.className).toMatch(/\bsm:w-auto\b/);
  const text = screen.getByText("#42").parentElement as HTMLElement;
  expect(text.className).toMatch(/\btext-left\b/);
  expect(text.className).toMatch(/\bsm:text-right\b/);
});
