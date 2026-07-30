import { render } from "@testing-library/react";
import { tokens } from "../theme";
import { EfficacyDotPlot, type EfficacyRow } from "./EfficacyDotPlot";

// si_spike from the fixture: CI [.49, .67] entirely clears null_rate .41.
const CLEARS: EfficacyRow = { hit_rate: 0.58, hit_ci_lo: 0.49, hit_ci_hi: 0.67, null_rate: 0.41 };
// rsi_oversold from the fixture: CI [.36, .56] straddles null_rate .5.
const DOES_NOT_CLEAR: EfficacyRow = { hit_rate: 0.46, hit_ci_lo: 0.36, hit_ci_hi: 0.56, null_rate: 0.5 };

test("degrades to a dash when any of hit_rate/ci_lo/ci_hi is null", () => {
  const { getByText, container } = render(
    <EfficacyDotPlot row={{ hit_rate: null, hit_ci_lo: null, hit_ci_hi: null, null_rate: 0.5 }} />,
  );
  expect(getByText("—")).toBeInTheDocument();
  expect(container.querySelector("svg")).toBeNull();
});

test("whisker x-coordinates are ordered ci_lo < dot < ci_hi", () => {
  const { container } = render(<EfficacyDotPlot row={CLEARS} />);
  const whisker = container.querySelector(".dot-whisker")!;
  const dot = container.querySelector(".dot-mark")!;
  const loX = Number(whisker.getAttribute("x1"));
  const hiX = Number(whisker.getAttribute("x2"));
  const dotX = Number(dot.getAttribute("cx"));
  expect(loX).toBeLessThan(dotX);
  expect(dotX).toBeLessThan(hiX);
});

test("dot wears the accent token only when the whole CI clears the baseline", () => {
  const { container: clears } = render(<EfficacyDotPlot row={CLEARS} />);
  expect(clears.querySelector(".dot-mark")).toHaveAttribute("fill", tokens.up);

  const { container: watch } = render(<EfficacyDotPlot row={DOES_NOT_CLEAR} />);
  expect(watch.querySelector(".dot-mark")).toHaveAttribute("fill", tokens.hold);
});

test("whisker and baseline band always wear neutral token colors, never the accent", () => {
  const { container } = render(<EfficacyDotPlot row={CLEARS} />);
  expect(container.querySelector(".dot-whisker")).toHaveAttribute("stroke", tokens.hold);
  expect(container.querySelector(".dot-baseline-band")).toHaveAttribute("fill", tokens.hold);
});

test("renders the hit-rate percent as visible text", () => {
  const { getByText } = render(<EfficacyDotPlot row={CLEARS} />);
  expect(getByText("58%")).toBeInTheDocument();
});
