import fixture from "./fixtures/data.json";
import { KICKERS, type DashboardDoc, type Kicker } from "./types";
import { STRAND_BLURBS, strandId, strandLabels, strandOfSection, strandSections } from "./strands";

const doc = fixture as unknown as DashboardDoc;

test("strandId slugs a label the way the route expects", () => {
  expect(strandId("Track record")).toBe("track-record");
  expect(strandId("Your book")).toBe("your-book");
});

test("strandLabels is the fixed kicker order, with Other only when a section's kicker is unknown", () => {
  expect(strandLabels(doc.sections)).toEqual([...KICKERS]);
  const drifted = { ...doc.sections, x: { title: "X", kicker: "Vibes" as unknown as Kicker } };
  expect(strandLabels(drifted)).toEqual([...KICKERS, "Other"]);
});

test("strandSections filters by kicker, and Other collects the strays", () => {
  const drifted = { ...doc.sections, x: { title: "X", kicker: "Vibes" as unknown as Kicker }, y: { title: "Y" } };
  expect(strandSections(drifted, "Macro").map(([id]) => id)).toContain("regime");
  expect(strandSections(drifted, "Other").map(([id]) => id)).toEqual(["x", "y"]);
});

test("strandOfSection resolves a section id to its strand slug, or null when unknown", () => {
  expect(strandOfSection(doc.sections, "scorecard")).toBe("signals");
  expect(strandOfSection(doc.sections, "equity-curve")).toBe("track-record");
  expect(strandOfSection(doc.sections, "no-such-section")).toBeNull();
});

test("every strand has a one-line blurb for the Summary index", () => {
  for (const label of KICKERS) expect(STRAND_BLURBS[label]).toMatch(/\S/);
});
