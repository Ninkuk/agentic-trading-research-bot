// The "suggest a name" box: a ticker becomes a prefilled GitHub issue on
// the repo's research-request template. No backend and no account state;
// the page never stores what is typed.

import { REPO_URL } from "../constants";
import type { DashboardDoc } from "../types";

/** US-listed symbols: 1–6 capitals, optionally a share-class suffix (BRK.B). */
export const TICKER_RE = /^[A-Z]{1,6}(\.[A-Z])?$/;

/** What the box keeps as it is typed: letters and one class-suffix dot,
 * uppercased. Digits, spaces and symbols never land in the field. */
export function normalizeTicker(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z.]/g, "").slice(0, 8);
}

export function suggestionHref(ticker: string): string {
  // `ticker` prefills the form's required field by its id; the title alone
  // leaves the field blank and the visitor retyping it.
  const q = new URLSearchParams({
    template: "research-request.yml",
    title: `Research: ${ticker}`,
    labels: "research-request",
    ticker,
  });
  return `${REPO_URL}/issues/new?${q.toString()}`;
}

export interface Known {
  symbol: string;
  /** The research call on file, lowercased, or null when not yet researched. */
  call: string | null;
}

/** Every symbol the desk already follows: the nightly scorecard's ~1,000
 * names, the candidate screen, and every researched name, with the
 * research call where one exists. Sorted; empty when no section is live. */
export function universe(doc: DashboardDoc): Known[] {
  const calls = new Map<string, string | null>();
  for (const id of ["scorecard", "candidates"]) {
    const sec = doc.sections[id];
    if (!sec || sec.error) continue;
    for (const r of sec.rows ?? []) if (typeof r.symbol === "string") calls.set(r.symbol, calls.get(r.symbol) ?? null);
  }
  const research = doc.sections["research"];
  if (research && !research.error) {
    for (const r of research.rows ?? []) {
      if (typeof r.ticker === "string") calls.set(r.ticker, String(r.call ?? "").toLowerCase() || null);
    }
  }
  return [...calls].map(([symbol, call]) => ({ symbol, call })).sort((a, b) => (a.symbol < b.symbol ? -1 : 1));
}

/** Symbols starting with the typed prefix, at most `n`; none for an
 * empty prefix. */
export function matches(known: Known[], prefix: string, n = 6): Known[] {
  if (prefix === "") return [];
  const out: Known[] = [];
  for (const k of known) {
    if (k.symbol.startsWith(prefix)) {
      out.push(k);
      if (out.length === n) break;
    }
  }
  return out;
}
