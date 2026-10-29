// The "suggest a name" box: a ticker becomes a prefilled GitHub issue on
// the repo's research-request template. No backend and no account state;
// the page never stores what is typed.

import { REPO_URL } from "../constants";

/** US-listed symbols: 1–6 capitals, optionally a share-class suffix (BRK.B). */
export const TICKER_RE = /^[A-Z]{1,6}(\.[A-Z])?$/;

/** What the box keeps as it is typed: letters and one class-suffix dot,
 * uppercased. Digits, spaces and symbols never land in the field. */
export function normalizeTicker(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z.]/g, "").slice(0, 8);
}

export function suggestionHref(ticker: string): string {
  const q = new URLSearchParams({
    template: "research-request.yml",
    title: `Research: ${ticker}`,
    labels: "research-request",
  });
  return `${REPO_URL}/issues/new?${q.toString()}`;
}
