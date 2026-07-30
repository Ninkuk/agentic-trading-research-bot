// Formatters for the dashboard's numeric/date display. Every formatter
// returns "—" for null/undefined/NaN — the fixture and the real export both
// carry nulls for "not yet computed" fields, and every table/tile must
// render that as a plain em-dash rather than "NaN" or "undefined".

const DASH = "—"; // —

function isBlank(v: number | null | undefined): v is null | undefined {
  return v === null || v === undefined || Number.isNaN(v);
}

/** Plain fixed-point number, grouped thousands, `dp` decimal places (default 2). */
export function num(v: number | null | undefined, dp = 2): string {
  if (isBlank(v)) return DASH;
  return v.toLocaleString("en-US", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}

/** Percent string, `dp` decimal places (default 1). Input is already
 * percent-scale (e.g. 62.3, not 0.623) — callers/exporters do that
 * conversion, this only appends the `%`. */
export function pct(v: number | null | undefined, dp = 1): string {
  if (isBlank(v)) return DASH;
  return `${num(v, dp)}%`;
}

/** Fixed-point number with an explicit leading sign (+/-). */
export function signed(v: number | null | undefined, dp = 2): string {
  if (isBlank(v)) return DASH;
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${num(Math.abs(v), dp)}`;
}

/** USD currency, 2 decimal places, `$` prefix, grouped thousands. */
export function usd(v: number | null | undefined): string {
  if (isBlank(v)) return DASH;
  const sign = v < 0 ? "-" : "";
  return `${sign}$${num(Math.abs(v), 2)}`;
}

/** "Jul 29" from an ISO date string ("2026-07-29" or a full timestamp).
 * Parses the calendar date directly out of the string (no Date/timezone
 * math) so a bare "YYYY-MM-DD" never shifts a day under local time. */
export function dateShort(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return DASH;
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  const monthIdx = Number(m[2]) - 1;
  if (monthIdx < 0 || monthIdx > 11) return DASH;
  return `${months[monthIdx]} ${Number(m[3])}`;
}
