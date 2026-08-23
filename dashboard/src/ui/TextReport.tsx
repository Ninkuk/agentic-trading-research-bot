// Structured rendering for text_lines report sections (today only the
// Trader scorecard). The scorecard report format is stable:
//
//   === <Title — period> ===
//   <blank>
//   Block heading (qualifier)
//     col | col | col
//     val | val | val
//   trailing note lines without pipes
//
// parseTextReport() lifts that into blocks; render falls back to the raw
// <pre> whenever the shape doesn't parse, so a format drift can never
// blank the section. (The class fix — the exporter emitting structured
// JSON instead of prose — is called out in the implementation plan; this
// parser is the no-Python-change version.)

import type { ReactNode } from "react";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";

interface ReportBlock {
  heading: string;
  qualifier: string | null;
  columns: string[];
  rows: string[][];
  notes: string[];
}

interface ParsedReport {
  title: string | null;
  blocks: ReportBlock[];
}

function parseTextReport(lines: string[]): ParsedReport | null {
  const rest = [...lines];
  let title: string | null = null;
  const first = rest.find((l) => l.trim().length > 0);
  const m = first ? /^=+\s*(.+?)\s*=+$/.exec(first.trim()) : null;
  if (m) {
    title = m[1];
    rest.splice(rest.indexOf(first!), 1);
  }

  // split into blank-line-separated groups
  const groups: string[][] = [];
  let cur: string[] = [];
  for (const line of rest) {
    if (line.trim() === "") {
      if (cur.length) groups.push(cur);
      cur = [];
    } else {
      cur.push(line);
    }
  }
  if (cur.length) groups.push(cur);

  const blocks: ReportBlock[] = [];
  for (const g of groups) {
    const headingLine = g[0].trim();
    const q = /^(.*?)\s*\((.+)\)$/.exec(headingLine);
    const pipeLines = g.slice(1).filter((l) => l.includes("|"));
    const notes = g
      .slice(1)
      .filter((l) => !l.includes("|"))
      .map((l) => l.trim());
    if (pipeLines.length < 2) {
      blocks.push({
        heading: q ? q[1] : headingLine,
        qualifier: q ? q[2] : null,
        columns: [],
        rows: [],
        notes: [...pipeLines.map((l) => l.trim()), ...notes],
      });
      continue;
    }
    const split = (l: string) => l.split("|").map((c) => c.trim());
    blocks.push({
      heading: q ? q[1] : headingLine,
      qualifier: q ? q[2] : null,
      columns: split(pipeLines[0]),
      rows: pipeLines.slice(1).map(split),
      notes,
    });
  }
  return blocks.length > 0 ? { title, blocks } : null;
}

/* ---------- rendering ---------- */

const NUM_RE = /^-?\d+(\.\d+)?%?$/;

function prettyHeader(h: string): string {
  const cleaned = h.replace(/_/g, " ");
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

/** Fraction columns (excess / return) arrive as raw decimals — show them
 * as signed tinted percents, like every other table on the page. */
function cell(value: string, header: string): ReactNode {
  const isFraction = /excess|return/i.test(header) && /^-?\d\.\d+$/.test(value);
  if (isFraction) {
    const v = Number(value);
    return (
      <span
        className={
          v > 0
            ? "text-emerald-700 dark:text-emerald-400"
            : v < 0
              ? "text-red-700 dark:text-red-400"
              : undefined
        }
      >
        {v > 0 ? "+" : ""}
        {(v * 100).toFixed(1)}%
      </span>
    );
  }
  return value;
}

export function TextReport({ lines }: { lines: string[] }) {
  const parsed = parseTextReport(lines);
  if (!parsed) {
    return (
      <pre className="bg-muted/50 overflow-x-auto rounded-lg border p-4 font-mono text-xs leading-relaxed">
        {lines.join("\n")}
      </pre>
    );
  }
  // "Trader Decision-Quality Scorecard — 2026-07" → surface the period.
  const period = parsed.title?.split("—")[1]?.trim() ?? null;
  return (
    <div className="space-y-5">
      {period && (
        // "period" labels the bare chip — an unlabeled "2026-08" reads as a
        // tag, not as the reporting month.
        <Badge variant="secondary">
          period <span className="font-mono">{period}</span>
        </Badge>
      )}
      {parsed.blocks.map((b) => {
        // A column is numeric when every non-empty value parses as one —
        // alignment then matches the data, not the column position.
        const numericCol = b.columns.map((_, ci) =>
          b.rows.every((r) => !r[ci] || NUM_RE.test(r[ci])),
        );
        return (
          <div key={b.heading} className="space-y-1.5">
            <div className="flex flex-wrap items-baseline gap-x-2">
              <h3 className="text-sm font-medium">{b.heading}</h3>
              {b.qualifier && <span className="text-muted-foreground text-xs">{b.qualifier}</span>}
            </div>
            {b.columns.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    {b.columns.map((c, i) => (
                      <TableHead key={i} className={`h-8 ${numericCol[i] ? "text-right" : ""}`}>
                        {prettyHeader(c)}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {b.rows.map((r, ri) => (
                    <TableRow key={ri}>
                      {r.map((v, ci) => (
                        <TableCell
                          key={ci}
                          className={`py-1.5 ${
                            numericCol[ci] ? "text-right font-mono tabular-nums" : ""
                          }`}
                        >
                          {cell(v, b.columns[ci] ?? "")}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {b.notes.map((n, ni) => (
              <p key={ni} className="text-muted-foreground text-xs">
                {n}
              </p>
            ))}
          </div>
        );
      })}
    </div>
  );
}
