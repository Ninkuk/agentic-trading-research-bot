import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import { groupBySource, strandSections } from "../strands";
import type { DashboardDoc } from "../types";
import { StrandNav } from "./StrandNav";

const doc = fixture as unknown as DashboardDoc;

test("one chip per publisher group, linking to the group anchor", () => {
  const groups = groupBySource(
    "sources",
    strandSections(doc.sections, "Sources"),
  );
  render(<StrandNav groups={groups} />);
  const nav = screen.getByRole("navigation", {
    name: "sections in this strand",
  });
  const links = Array.from(nav.querySelectorAll("a"));
  expect(links.map((a) => a.textContent)).toEqual(groups.map((g) => g.label));
  expect(links[0]).toHaveAttribute("href", "#sources-treasury");
  // No IntersectionObserver under jsdom: nothing is current yet.
  expect(nav.querySelector("[aria-current]")).toBeNull();
});

test("a source-less section's chip carries its own title and id", () => {
  render(
    <StrandNav
      groups={groupBySource("other", [["lone", { title: "Lone card" }]])}
    />,
  );
  expect(screen.getByRole("link", { name: "Lone card" })).toHaveAttribute(
    "href",
    "#lone",
  );
});
