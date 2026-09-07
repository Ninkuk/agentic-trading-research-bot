import fixture from "./fixtures/data.json";
import { KICKERS, type DashboardDoc, type Kicker } from "./types";
import {
  STRAND_BLURBS,
  groupBySource,
  showsGroups,
  strandId,
  strandItems,
  strandLabels,
  strandOfAnchor,
  strandOfSection,
  strandSections,
} from "./strands";

const doc = fixture as unknown as DashboardDoc;

test("strandId slugs a label the way the route expects", () => {
  expect(strandId("Track record")).toBe("track-record");
  expect(strandId("Your book")).toBe("your-book");
});

test("strandLabels is the fixed kicker order, with Other only when a section's kicker is unknown", () => {
  expect(strandLabels(doc.sections)).toEqual([...KICKERS]);
  const drifted = {
    ...doc.sections,
    x: { title: "X", kicker: "Vibes" as unknown as Kicker },
  };
  expect(strandLabels(drifted)).toEqual([...KICKERS, "Other"]);
});

test("strandSections filters by kicker, and Other collects the strays", () => {
  const drifted = {
    ...doc.sections,
    x: { title: "X", kicker: "Vibes" as unknown as Kicker },
    y: { title: "Y" },
  };
  expect(strandSections(drifted, "Macro").map(([id]) => id)).toContain(
    "regime",
  );
  expect(strandSections(drifted, "Other").map(([id]) => id)).toEqual([
    "x",
    "y",
  ]);
});

test("strandOfSection resolves a section id to its strand slug, or null when unknown", () => {
  expect(strandOfSection(doc.sections, "scorecard")).toBe("signals");
  expect(strandOfSection(doc.sections, "equity-curve")).toBe("track-record");
  expect(strandOfSection(doc.sections, "no-such-section")).toBeNull();
});

test("every strand has a one-line blurb for the Summary index", () => {
  for (const label of KICKERS) expect(STRAND_BLURBS[label]).toMatch(/\S/);
});

test("groupBySource groups a strand by publisher in first-appearance order, moving siblings together", () => {
  const groups = groupBySource(
    "sources",
    strandSections(doc.sections, "Sources"),
  );
  expect(groups.map((g) => g.label)).toEqual([
    "Treasury",
    "NY Fed",
    "FRED",
    "CFTC",
    "FINRA",
    "SEC",
    "CBOE",
    "Earnings",
    "EIA",
    "USDA",
    "Reddit",
  ]);
  const treasury = groups[0];
  expect(treasury.anchor).toBe("sources-treasury");
  // auction-demand sits after the CFTC cards in exporter order; grouping pulls it up.
  expect(treasury.entries.map(([id]) => id)).toEqual([
    "federal-debt",
    "auction-demand",
    "upcoming-auctions",
  ]);
});

test("a section with no source is its own group, anchored on its own id", () => {
  const groups = groupBySource("other", [
    ["a", { title: "Alpha" }],
    ["b", { title: "Beta", source: "SEC" }],
    ["c", { title: "Gamma", source: "SEC" }],
  ]);
  expect(
    groups.map((g) => [g.label, g.source, g.anchor, g.entries.length]),
  ).toEqual([
    ["Alpha", undefined, "a", 1],
    ["SEC", "SEC", "other-sec", 2],
  ]);
});

test("showsGroups needs a long strand with more than one group", () => {
  const sources = strandSections(doc.sections, "Sources");
  expect(showsGroups(sources, groupBySource("sources", sources))).toBe(true);
  const macro = strandSections(doc.sections, "Macro");
  expect(showsGroups(macro, groupBySource("macro", macro))).toBe(false);
  const oneGroup = sources.map(
    ([id, sec]) => [id, { ...sec, source: "SEC" }] as [string, typeof sec],
  );
  expect(showsGroups(oneGroup, groupBySource("sources", oneGroup))).toBe(false);
  // A long strand of source-less cards is many singletons, not a grouping.
  const noSource = sources.map(
    ([id, sec]) => [id, { ...sec, source: undefined }] as [string, typeof sec],
  );
  expect(showsGroups(noSource, groupBySource("sources", noSource))).toBe(false);
});

test("strandOfAnchor resolves a group anchor to its strand slug", () => {
  const labels = strandLabels(doc.sections);
  expect(strandOfAnchor(labels, "sources-sec")).toBe("sources");
  expect(strandOfAnchor(labels, "track-record-x")).toBe("track-record");
  expect(strandOfAnchor(labels, "equity-curve")).toBeNull();
});

test("strandItems lists publishers for a grouped strand and live sections otherwise", () => {
  const macro = strandItems("macro", strandSections(doc.sections, "Macro"));
  expect(macro.map((it) => it.anchor)).toContain("regime");
  expect(macro.find((it) => it.anchor === "regime")).toEqual({
    label: "Regime",
    anchor: "regime",
    ids: ["regime"],
  });
  const sourced = Array.from({ length: 8 }, (_, i) => [
    `s${i}`,
    { title: `S${i}`, source: i % 2 ? "SEC" : "FINRA", rows: [{ x: 1 }] },
  ]) as [string, { title: string; source: string; rows: { x: number }[] }][];
  expect(strandItems("sources", sourced)).toEqual([
    { label: "FINRA", anchor: "sources-finra", ids: ["s0", "s2", "s4", "s6"] },
    { label: "SEC", anchor: "sources-sec", ids: ["s1", "s3", "s5", "s7"] },
  ]);
  // Quiet sections never become items.
  expect(strandItems("x", [["q", { title: "Q", empty: "nothing" }]])).toEqual(
    [],
  );
});
