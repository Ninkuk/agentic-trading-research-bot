import fixture from "../fixtures/data.json";
import type { DashboardDoc, Section } from "../types";
import {
  bestCall,
  calibration,
  callHitRate,
  decisionDeck,
  callsGraded,
  drivers,
  firstNight,
  lastNight,
  lastRunOf,
  lastRuns,
  plainSummary,
  newestThesis,
  nightsCalled,
  record,
  researchCounts,
  scoredSymbols,
  stocksBought,
  thesisCallout,
  thesisHeadings,
  thesisKillVerdict,
  thesisOneLiner,
  unprovenSignals,
} from "./homeFacts";

const doc = fixture as unknown as DashboardDoc;

function withSection(id: string, sec: Section | undefined): DashboardDoc {
  const sections = { ...doc.sections };
  if (sec === undefined) delete sections[id];
  else sections[id] = sec;
  return { ...doc, sections };
}

test("researchCounts tallies calls and attack verdicts over every row", () => {
  const c = researchCounts(doc);
  expect(c).not.toBeNull();
  expect(c!.theses).toBe(doc.sections["research"].rows!.length);
  expect(c!.passes + c!.buys).toBe(c!.theses);
  expect(c!.sound + c!.flawed + c!.unproven).toBeLessThanOrEqual(c!.theses);
});

test("researchCounts is null without research rows or on an errored section", () => {
  expect(researchCounts(withSection("research", undefined))).toBeNull();
  expect(researchCounts(withSection("research", { error: "missing" }))).toBeNull();
});

test("newestThesis picks the latest thesis_date and lowercases the call", () => {
  const d = withSection("research", {
    rows: [
      { ticker: "OLD", thesis_date: "2026-07-01", call: "PASS", verdict: "SOUND" },
      { ticker: "NEW", thesis_date: "2026-07-09", call: "BUY", verdict: null },
      { ticker: "MID", thesis_date: "2026-07-05", call: "PASS", verdict: "FLAWED" },
    ],
  });
  expect(newestThesis(d)).toEqual({ ticker: "NEW", date: "2026-07-09", call: "buy", verdict: null });
});

test("scoredSymbols takes the scorecard's first rows with lean and flag", () => {
  const out = scoredSymbols(doc, 2);
  expect(out.map((s) => s.symbol)).toEqual(doc.sections["scorecard"].rows!.slice(0, 2).map((r) => r.symbol));
  expect(out[0]).toEqual({ symbol: "AAPL", score: 4, flagged: true });
  expect(scoredSymbols(withSection("scorecard", { rows: [] }), 5)).toEqual([]);
});

test("stocksBought counts distinct journaled buy symbols", () => {
  const d = withSection("your-trades", { rows: [
    { symbol: "A", side: "buy" }, { symbol: "A", side: "buy" }, { symbol: "B", side: "buy" }, { symbol: "C", side: "sell" },
  ] });
  expect(stocksBought(d)).toBe(2);
  expect(stocksBought(withSection("your-trades", { rows: [] }))).toBeNull();
});

test("decisionDeck deals the newest write-ups oldest-first, keeping a few buys in", () => {
  const d = withSection("research", {
    rows: [
      { ticker: "A", call: "PASS", thesis_date: "2026-07-01" },
      { ticker: "B", call: "BUY", thesis_date: "2026-07-02" },
      { ticker: "C", call: "PASS", thesis_date: "2026-07-03" },
      { ticker: "D", call: "BUY", thesis_date: "2026-07-04" },
      { ticker: "E", call: "PASS", thesis_date: "2026-07-05" },
      { ticker: "F", call: "HOLD", thesis_date: "2026-07-06" },
    ],
  });
  expect(decisionDeck(d, 3, 1).map((c) => `${c.ticker}:${c.call}`)).toEqual(["C:pass", "D:buy", "E:pass"]);
  expect(decisionDeck(d, 10, 1).map((c) => c.ticker)).toEqual(["A", "C", "D", "E"]);
  expect(decisionDeck(withSection("research", { rows: [] }))).toEqual([]);
});

test("firstNight is the timeline's earliest date", () => {
  const dates = doc.sections["regime-timeline"].rows!.map((r) => String(r.date)).sort();
  expect(firstNight(doc)).toBe(dates[0]);
  expect(firstNight(withSection("regime-timeline", { rows: [] }))).toBeNull();
});

test("nightsCalled prefers the exporter's total over the capped row count", () => {
  expect(nightsCalled(doc)).toBe(doc.sections["regime-timeline"].rows!.length);
  expect(nightsCalled(withSection("regime-timeline", { rows: [{ date: "x" }], total: 119 }))).toBe(119);
  expect(nightsCalled(withSection("regime-timeline", { rows: [] }))).toBeNull();
});

const calib: Section = {
  verdict: { text: "Confidence matched results: said 46%, won 44%", tone: "mid" },
  tiles: [
    { label: "Forecast error", value: "0.24", band: "21 days out · guessing the base rate scores 0.25 · 93 calls", tone: "on" },
    { label: "Said vs won", value: "46% vs 44%", band: null, tone: null },
  ],
  rows: [
    { horizon: 5, p_bin: "30–40%", n: 14, n_dates: 11 },
    { horizon: 21, p_bin: "30–40%", n: 60, n_dates: 20 },
    { horizon: 21, p_bin: "40–50%", n: 33, n_dates: 14 },
  ],
};

test("callsGraded sums the 21-day calibration bins only", () => {
  expect(callsGraded(withSection("research-calibration", calib))).toBe(93);
  expect(callsGraded(doc)).toBeNull(); // fixture carries no calibration rows
});

test("calibration carries the verdict, the forecast error, and the base-rate score", () => {
  expect(calibration(withSection("research-calibration", calib))).toEqual({
    verdict: calib.verdict,
    forecastError: "0.24",
    baseRate: "0.25",
  });
  expect(calibration(doc)).toBeNull();
});

test("callHitRate pins the 21-day row for the requested call", () => {
  const d = withSection("research-filter", {
    rows: [
      { verdict: "buy", horizon: 5, n: 57, hit_rate: 0.42 },
      { verdict: "buy", horizon: 21, n: 45, hit_rate: 0.556 },
      { verdict: "pass", horizon: 21, n: 234, hit_rate: 0.581 },
    ],
  });
  expect(callHitRate(d, "buy")).toEqual({ rate: 0.556, n: 45 });
  expect(callHitRate(d, "pass")).toEqual({ rate: 0.581, n: 234 });
  expect(callHitRate(doc, "buy")).toBeNull();
});

test("unprovenSignals counts distinct signals, unproven only when every horizon is", () => {
  const d = withSection("signal-recommendations", {
    rows: [
      { signal_id: "a", horizon: 5, recommendation: "insufficient evidence" },
      { signal_id: "a", horizon: 21, recommendation: "insufficient evidence" },
      { signal_id: "b", horizon: 5, recommendation: "insufficient evidence" },
      { signal_id: "b", horizon: 21, recommendation: "keep" },
    ],
  });
  expect(unprovenSignals(d)).toEqual({ unproven: 1, total: 2 });
  expect(unprovenSignals(withSection("signal-recommendations", { rows: [] }))).toBeNull();
});

test("record uses the exporter's tiles and curve, never recomputing", () => {
  const r = record(doc);
  expect(r).not.toBeNull();
  const sec = doc.sections["equity-curve"];
  expect(r!.rows).toBe(sec.curve);
  expect(r!.since).toBe(sec.curve![0].date);
  expect(r!.tradingDays).toBe(sec.curve_summary!.trading_days);
  expect(r!.picks).toBe(String(sec.tiles![0].value));
  expect(record(withSection("equity-curve", { ...sec, curve: [sec.curve![0]] }))).toBeNull();
  expect(record(withSection("equity-curve", { error: "no advisor.db" }))).toBeNull();
});

test("lastNight reads each step's live output and nulls what is missing", () => {
  const n = lastNight(doc);
  expect(n.jobsRan).toBe(doc.sections["health"].tiles![0].value);
  expect(n.regime).toBe(doc.sections["regime"].verdict!.text);
  const sc = doc.sections["scorecard"];
  expect(n.tickersScored).toBe(sc.total ?? sc.rows!.length);
  expect(n.thesis).toEqual(newestThesis(doc));
  const cand = doc.sections["candidates"];
  expect(n.candidates).toBe(cand.total ?? cand.rows!.length);
  const bare = lastNight({ ...doc, sections: {} });
  expect(bare).toEqual({
    jobsRan: null,
    regime: null,
    tickersScored: null,
    candidates: null,
    callsGraded: null,
    thesis: null,
  });
});

test("lastRuns replays the health section's runs in order and by job", () => {
  const runs = lastRuns(doc);
  expect(runs.map((r) => r.job)).toEqual(["treasury", "fred", "edgar", "composite", "scorer", "research-nightly"]);
  expect(lastRunOf(doc, "scorer")!.summary).toMatch(/^scorer snapshot 130/);
  expect(lastRunOf(doc, "nope")).toBeNull();
  expect(lastRuns(withSection("health", { error: "no logs" }))).toEqual([]);
  expect(lastRuns(withSection("health", { tiles: [] }))).toEqual([]);
});

test("plainSummary phrases each job's numbers for a reader, else keeps the line", () => {
  const fred = lastRunOf(doc, "fred")!;
  expect(plainSummary(fred)).toBe("142,314 data points across 31 economic series, from the Federal Reserve");
  expect(plainSummary(lastRunOf(doc, "edgar")!)).toBe("4,341 new company filings, from the SEC");
  expect(plainSummary({ ...fred, job: "scorer" })).toBe(fred.summary);
  expect(plainSummary({ ...fred, summary: null })).toBeNull();
});

test("drivers lists the macro tiles with their band words", () => {
  const d = withSection("macro-drivers", {
    tiles: [
      { label: "Fear index (VIX)", value: 17.52, band: "normal", tone: null },
      { label: "Junk-bond premium", value: 3.18, band: "calm", tone: null },
      { label: "Missing", value: null, band: null, tone: null },
    ],
  });
  expect(drivers(d)).toEqual([
    { label: "Fear index (VIX)", value: "17.52", band: "normal" },
    { label: "Junk-bond premium", value: "3.18", band: "calm" },
  ]);
  expect(drivers(withSection("macro-drivers", undefined))).toEqual([]);
});

test("thesisCallout pulls any labelled callout; thesisKillVerdict reads the attack's label", () => {
  const md = "> [!WARNING]\n> **Closest attack:** the moat is\n> thinner than it looks.\n\nkill-thesis: **FLAWED** —\n";
  expect(thesisCallout(md, "Closest attack")).toBe("the moat is thinner than it looks.");
  expect(thesisCallout(md, "In one sentence")).toBeNull();
  expect(thesisKillVerdict(md)).toBe("flawed");
  expect(thesisKillVerdict("no label")).toBeNull();
});

test("thesisHeadings lists the ## sections in order", () => {
  expect(thesisHeadings("# T\n\n## 1. Verdict\ntext\n### sub\n## 2. Business\n##  \n")).toEqual(["1. Verdict", "2. Business"]);
  expect(thesisHeadings("no headings")).toEqual([]);
});

test("thesisOneLiner joins the wrapped callout line and stops at the next block", () => {
  const md = [
    "# PRI — Primerica — 2026-10-28",
    "",
    "> [!IMPORTANT]",
    "> **In one sentence:** Tinder's owner is a 33%-FCF-margin subscription business",
    "> whose price assumes decline, so pass.",
    "",
    "Price $279.06",
  ].join("\n");
  expect(thesisOneLiner(md)).toBe(
    "Tinder's owner is a 33%-FCF-margin subscription business whose price assumes decline, so pass.",
  );
  expect(thesisOneLiner("# No callout\n\nbody")).toBeNull();
  const single = "> [!IMPORTANT]\n> **In one sentence:** Buy.\n> **Next:** other\n";
  expect(thesisOneLiner(single)).toBe("Buy.");
});

test("bestCall is the exporter's pick, or null without a graded buy", () => {
  expect(bestCall(doc)).toEqual(doc.sections["research-verdict-outcomes"].best_call);
  const sec = doc.sections["research-verdict-outcomes"];
  expect(bestCall(withSection("research-verdict-outcomes", { ...sec, best_call: null }))).toBeNull();
  expect(bestCall(withSection("research-verdict-outcomes", { error: "no scorer.db" }))).toBeNull();
});
