import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Masthead } from "./Masthead";

beforeEach(() => {
  location.hash = "";
});

test("renders edition date and snapshot number", () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={42} />);
  expect(screen.getByText("July 28, 2026")).toBeInTheDocument();
  expect(screen.getByText("#42")).toBeInTheDocument();
});

test("omits the snapshot line when snapshotNumber is null", () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={null} />);
  expect(screen.queryByText(/^#/)).not.toBeInTheDocument();
});

test("uppercases the typed value and navigates to the ticker route on Enter", async () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={1} />);
  const input = screen.getByRole("textbox", { name: /search ticker/i });
  await userEvent.type(input, "deck");
  expect(input).toHaveValue("DECK");
  await userEvent.keyboard("{Enter}");
  expect(location.hash).toBe("#/ticker/DECK");
});

test("Enter with an empty box is a no-op", async () => {
  render(<Masthead editionDate="July 28, 2026" snapshotNumber={1} />);
  const input = screen.getByRole("textbox", { name: /search ticker/i });
  input.focus();
  await userEvent.keyboard("{Enter}");
  expect(location.hash).toBe("");
});
