import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrandNav } from "./StrandNav";

const STRANDS = [
  { id: "macro", label: "Macro" },
  { id: "signals", label: "Signals" },
];

beforeEach(() => {
  location.hash = "";
  document.body.innerHTML = "";
});

test("renders one link per strand", () => {
  render(<StrandNav strands={STRANDS} />);
  expect(screen.getByRole("link", { name: "Macro" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Signals" })).toBeInTheDocument();
});

test("clicking a strand link sets location.hash", async () => {
  // Give the nav a target section to scroll to (jsdom has no scrollIntoView
  // implementation, so the click handler guards it with optional chaining
  // — the assertion here is on the hash, not on real scrolling).
  const target = document.createElement("section");
  target.id = "signals";
  document.body.appendChild(target);

  render(<StrandNav strands={STRANDS} />);
  await userEvent.click(screen.getByRole("link", { name: "Signals" }));
  expect(location.hash).toBe("#signals");
});
