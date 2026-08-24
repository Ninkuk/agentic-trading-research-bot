import { render, screen } from "@testing-library/react";
import { ExtLink } from "./ExtLink";

test("an external link is underlined, opens in a new tab, and carries an out icon", () => {
  render(<ExtLink href="https://example.com/x">thesis</ExtLink>);
  const link = screen.getByRole("link", { name: "thesis" });
  expect(link).toHaveAttribute("href", "https://example.com/x");
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noreferrer");
  expect(link).toHaveClass("ext-link");
  expect(link.querySelector("svg")).toBeInTheDocument();
});
