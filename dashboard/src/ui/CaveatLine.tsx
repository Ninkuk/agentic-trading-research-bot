// The standard "how much to trust this" footnote — every table/section that
// carries a statistical caveat (multiple comparisons, small n, ...) renders
// it through this one component so it always reads the same way.

export interface CaveatLineProps {
  text: string;
}

export function CaveatLine({ text }: CaveatLineProps) {
  return <p className="cap caveat-line">{text}</p>;
}
