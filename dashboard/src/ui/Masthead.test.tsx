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
