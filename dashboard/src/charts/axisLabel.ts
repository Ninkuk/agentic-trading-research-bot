// Grain tiles' history is annual and keyed by crop year ("2007"), which
// dateShort would render as a dash.

import { dateShort } from "../format";

export function axisLabel(date: string | undefined): string {
  return date && /^\d{4}$/.test(date) ? date : dateShort(date);
}
