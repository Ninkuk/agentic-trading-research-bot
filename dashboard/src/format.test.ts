import { num, pct, signed, usd, dateShort } from "./format";

test("num formats with fixed decimals and dash for null/undefined", () => {
  expect(num(1234.5)).toBe("1,234.50");
  expect(num(1, 0)).toBe("1");
  expect(num(null)).toBe("—");
  expect(num(undefined)).toBe("—");
  expect(num(NaN)).toBe("—");
});

test("pct appends % and dashes null", () => {
  expect(pct(62.345)).toBe("62.3%");
  expect(pct(0, 0)).toBe("0%");
  expect(pct(null)).toBe("—");
  expect(pct(undefined)).toBe("—");
});

test("signed prefixes +/- and dashes null", () => {
  expect(signed(4.2)).toBe("+4.20");
  expect(signed(-4.2)).toBe("−4.20");
  expect(signed(0)).toBe("0.00");
  expect(signed(null)).toBe("—");
});

test("usd prefixes $ and handles negatives / null", () => {
  expect(usd(1234.5)).toBe("$1,234.50");
  expect(usd(-99.9)).toBe("-$99.90");
  expect(usd(null)).toBe("—");
  expect(usd(undefined)).toBe("—");
});

test("dateShort renders month-day from an ISO date and dashes bad input", () => {
  expect(dateShort("2026-07-29")).toBe("Jul 29");
  expect(dateShort("2026-01-05T04:12:00+00:00")).toBe("Jan 5");
  expect(dateShort(null)).toBe("—");
  expect(dateShort(undefined)).toBe("—");
  expect(dateShort("not-a-date")).toBe("—");
});
