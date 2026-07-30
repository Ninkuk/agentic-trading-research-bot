// Trimmed port of shadcn/ui's chart.tsx (Recharts wrapper): ChartContainer
// injects per-chart CSS color variables from a ChartConfig (theme-aware via
// the .dark selector), ChartTooltipContent replaces Recharts' default
// white-box tooltip with a token-styled one. Legend omitted — the lab
// doesn't need it.

import {
  createContext,
  useContext,
  useId,
  type ComponentProps,
  type CSSProperties,
  type ReactNode,
} from "react";
import * as RechartsPrimitive from "recharts";
import { cn } from "./utils";

const THEMES = { light: "", dark: ".dark" } as const;

export type ChartConfig = Record<
  string,
  {
    label?: ReactNode;
    color?: string;
    theme?: Record<keyof typeof THEMES, string>;
  }
>;

const ChartContext = createContext<{ config: ChartConfig } | null>(null);

function useChart() {
  const ctx = useContext(ChartContext);
  if (!ctx) throw new Error("useChart must be used within a <ChartContainer />");
  return ctx;
}

export function ChartContainer({
  id,
  className,
  children,
  config,
  ...props
}: ComponentProps<"div"> & {
  config: ChartConfig;
  children: ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
}) {
  const uniqueId = useId();
  const chartId = `chart-${id || uniqueId.replace(/:/g, "")}`;
  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-chart={chartId}
        className={cn(
          "flex aspect-video justify-center text-xs",
          "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground",
          "[&_.recharts-cartesian-grid_line[stroke='#ccc']]:stroke-border/50",
          "[&_.recharts-curve.recharts-tooltip-cursor]:stroke-border",
          "[&_.recharts-layer]:outline-hidden [&_.recharts-surface]:outline-hidden",
          className,
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer>{children}</RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
}

// The injected CSS is built from developer-authored ChartConfig constants,
// but sanitize anyway: keys to a css-ident charset, colors must look like a
// color function / hex / var() reference (defense-in-depth on the upstream
// shadcn dangerouslySetInnerHTML pattern).
const SAFE_KEY = /^[a-zA-Z][a-zA-Z0-9_-]*$/;
const SAFE_COLOR = /^(#[0-9a-fA-F]{3,8}|(var|oklch|rgb|rgba|hsl|hsla)\([^;{}]*\))$/;

function ChartStyle({ id, config }: { id: string; config: ChartConfig }) {
  const colorConfig = Object.entries(config).filter(
    ([key, c]) => SAFE_KEY.test(key) && (c.theme || c.color),
  );
  if (!colorConfig.length) return null;
  return (
    <style
      dangerouslySetInnerHTML={{
        __html: Object.entries(THEMES)
          .map(
            ([theme, prefix]) => `
${prefix} [data-chart=${id}] {
${colorConfig
  .map(([key, c]) => {
    const color = c.theme?.[theme as keyof typeof THEMES] || c.color;
    return color && SAFE_COLOR.test(color) ? `  --color-${key}: ${color};` : null;
  })
  .filter(Boolean)
  .join("\n")}
}`,
          )
          .join("\n"),
      }}
    />
  );
}

export const ChartTooltip = RechartsPrimitive.Tooltip;

interface TooltipItem {
  dataKey?: string | number;
  name?: string | number;
  value?: number | string;
  color?: string;
  payload?: Record<string, unknown>;
}

export function ChartTooltipContent({
  active,
  payload,
  label,
  labelFormatter,
  valueFormatter,
}: {
  active?: boolean;
  payload?: TooltipItem[];
  label?: string | number;
  labelFormatter?: (label: string | number) => ReactNode;
  valueFormatter?: (value: number | string) => ReactNode;
}) {
  const { config } = useChart();
  if (!active || !payload?.length) return null;
  return (
    <div className="border-border/50 bg-background grid min-w-32 items-start gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs shadow-xl">
      {label !== undefined && (
        <div className="font-medium">{labelFormatter ? labelFormatter(label) : label}</div>
      )}
      <div className="grid gap-1.5">
        {payload.map((item) => {
          const key = String(item.dataKey ?? item.name ?? "value");
          const itemConfig = config[key];
          return (
            <div key={key} className="flex w-full items-center gap-2">
              <div
                className="size-2.5 shrink-0 rounded-[2px]"
                style={{ background: `var(--color-${key}, ${item.color ?? "currentColor"})` } as CSSProperties}
              />
              <div className="flex flex-1 items-center justify-between gap-4 leading-none">
                <span className="text-muted-foreground">{itemConfig?.label ?? key}</span>
                <span className="text-foreground font-mono font-medium tabular-nums">
                  {item.value !== undefined
                    ? valueFormatter
                      ? valueFormatter(item.value)
                      : item.value
                    : "—"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
