import { render, screen } from "@testing-library/react";
import { VERDICT_MIX_WIDTH, VerdictMix, verdictSegments } from "./VerdictMix";

test("segment widths plus 2px gaps span the full bar, in count order", () => {
  const segs = verdictSegments({ SOUND: 47, UNPROVEN: 68, FLAWED: 17 });
  expect(segs.map((s) => s.key)).toEqual(["SOUND", "UNPROVEN", "FLAWED"]);
  const total = segs.reduce((sum, s) => sum + s.width, 0) + 2 * (segs.length - 1);
  expect(total).toBeCloseTo(VERDICT_MIX_WIDTH, 6);
  // UNPROVEN is 68/132 of the usable width (600 − 2 gaps)
  expect(segs[1].width).toBeCloseTo((68 / 132) * (VERDICT_MIX_WIDTH - 4), 6);
  expect(segs[1].x).toBeCloseTo(segs[0].width + 2, 6);
});

test("a zero-count verdict takes no segment and no gap", () => {
  const segs = verdictSegments({ SOUND: 10, UNPROVEN: 0, FLAWED: 10 });
  expect(segs.map((s) => s.key)).toEqual(["SOUND", "FLAWED"]);
  expect(segs[0].width + segs[1].width + 2).toBeCloseTo(VERDICT_MIX_WIDTH, 6);
});

test("renders nothing for a total of 0", () => {
  const { container } = render(<VerdictMix counts={{ SOUND: 0, UNPROVEN: 0, FLAWED: 0 }} />);
  expect(container.firstChild).toBeNull();
});

test("labels each segment with its verdict word and count in text", () => {
  const { container } = render(<VerdictMix counts={{ SOUND: 47, UNPROVEN: 68, FLAWED: 17 }} />);
  expect(container.querySelectorAll("rect[data-verdict]").length).toBe(3);
  expect(screen.getByText("SOUND")).toBeInTheDocument();
  expect(screen.getByText("47")).toBeInTheDocument();
  expect(screen.getByText("FLAWED")).toBeInTheDocument();
  expect(screen.getByText("17")).toBeInTheDocument();
});
