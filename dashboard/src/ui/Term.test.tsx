import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Term } from "./Term";

test("popover opens on click and closes on Escape", async () => {
  render(
    <Term term="ATR" glossary={{ ATR: "average true range." }}>
      ATR
    </Term>,
  );
  await userEvent.click(screen.getByRole("button", { name: "ATR" }));
  expect(screen.getByText(/average true range/)).toBeVisible();
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByText(/average true range/)).not.toBeInTheDocument();
});

test("unknown term renders children without popover button", () => {
  render(
    <Term term="Nope" glossary={{}}>
      Nope
    </Term>,
  );
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.getByText("Nope")).toBeInTheDocument();
});

test("popover opens on hover and closes on mouse leave", async () => {
  render(
    <Term term="VIX" glossary={{ VIX: "volatility index." }}>
      VIX
    </Term>,
  );
  const trigger = screen.getByRole("button", { name: "VIX" });
  await userEvent.hover(trigger);
  expect(screen.getByText(/volatility index/)).toBeVisible();
  await userEvent.unhover(trigger);
  expect(screen.queryByText(/volatility index/)).not.toBeInTheDocument();
});
