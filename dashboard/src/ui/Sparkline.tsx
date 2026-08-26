// Inline table sparkline: a bare SVG polyline for a per-row number array
// (data.py's `history` columns). Pure SVG rather than a recharts
// ChartContainer — a leaderboard renders thirty of these per card, and
// thirty responsive chart containers measure the DOM on every resize.
// Scale-free: each line spans its own min..max, so it shows shape, not
// level (the level is the numeric column beside it).

const W = 84;
const H = 22;
const PAD = 2;

export interface SparklineProps {
  values: number[];
  label?: string;
}

function sparklinePoints(values: number[], w = W, h = H, pad = PAD): string {
  const n = values.length;
  if (n === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const stepX = n > 1 ? (w - pad * 2) / (n - 1) : 0;
  return values
    .map((v, i) => {
      const x = pad + i * stepX;
      const y = h - pad - ((v - min) / span) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function Sparkline({ values, label }: SparklineProps) {
  const clean = values.filter((v) => typeof v === "number" && Number.isFinite(v));
  if (clean.length < 3) return <span className="text-muted-foreground">—</span>;
  const pts = sparklinePoints(clean);
  const last = clean[clean.length - 1];
  const first = clean[0];
  const title = label
    ? `${label}: ${clean.length} points, ${first} → ${last}`
    : `${clean.length} points, ${first} → ${last}`;
  const [lx, ly] = pts.split(" ").at(-1)?.split(",") ?? ["0", "0"];
  return (
    <svg
      className="sparkline inline-block align-middle"
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      <polyline
        points={pts}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={lx} cy={ly} r="1.8" fill="var(--primary)" />
    </svg>
  );
}
