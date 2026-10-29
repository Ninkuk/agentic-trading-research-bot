// Hero statistics in the "number ticker" style: each value counts up from
// zero on a spring when the row scrolls into view, the cards blur in with a
// short stagger, and dividers rather than boxes separate them. Own
// implementation on motion; no Aceternity source is used. A value that is
// not a plain number (a signed percentage) ticks its numeric part and keeps
// its prefix and suffix. Under reduced motion the final value renders at
// once.

import { motion, useInView, useReducedMotion, useSpring, useTransform } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { EncryptedText } from "../components/aceternity/encrypted-text";

export interface Stat {
  /** A number, or a string like "+7.79%" whose digits tick. */
  value: number | string;
  label: string;
  /** false: show the value as it is ("92nd night" has no sensible count-up). */
  tick?: boolean;
  /** Seconds to hold the value scrambled before it decrypts into place
   * (the answer to the stat before it). Replaces the count-up. */
  revealAfter?: number;
}

function split(value: number | string): { prefix: string; n: number; suffix: string; decimals: number } {
  if (typeof value === "number") return { prefix: "", n: value, suffix: "", decimals: 0 };
  const m = /^([^\d]*)(\d[\d,]*(?:\.\d+)?)(.*)$/.exec(value.trim());
  if (!m) return { prefix: value, n: 0, suffix: "", decimals: 0 };
  const digits = m[2].replace(/,/g, "");
  const decimals = digits.includes(".") ? digits.split(".")[1].length : 0;
  return { prefix: m[1], n: Number(digits), suffix: m[3], decimals };
}

function Reveal({ value, start, after }: { value: number | string; start: boolean; after: number }) {
  const [go, setGo] = useState(false);
  const reduce = useReducedMotion();
  useEffect(() => {
    if (!start) return;
    const t = setTimeout(() => setGo(true), after * 1000);
    return () => clearTimeout(t);
  }, [start, after]);
  const text = String(value);
  if (reduce || go) return <EncryptedText text={text} revealDelayMs={160} flipDelayMs={50} encryptedClassName="text-muted-foreground/50" />;
  // Held: scrambled digits of the same width, never the answer.
  return (
    <span className="text-muted-foreground/50 tabular-nums" aria-label={text}>
      {text.replace(/\d/g, "#")}
    </span>
  );
}

function Ticker({ value, start, tick = true }: { value: number | string; start: boolean; tick?: boolean }) {
  const { prefix, n, suffix, decimals } = split(value);
  const reduce = useReducedMotion();
  const spring = useSpring(0, { mass: 0.8, stiffness: 75, damping: 15 });
  const text = useTransform(spring, (v) =>
    v.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }),
  );
  useEffect(() => {
    if (start) spring.set(n);
  }, [start, n, spring]);
  if (!tick) return <span className="tabular-nums">{value}</span>;
  if (reduce || !start) {
    const shown = reduce ? n : 0;
    return (
      <span className="tabular-nums">
        {prefix}
        {shown.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
        {suffix}
      </span>
    );
  }
  return (
    <span className="tabular-nums">
      {prefix}
      <motion.span>{text}</motion.span>
      {suffix}
    </span>
  );
}

export function StatTicker({ stats, className }: { stats: Stat[]; className?: string }) {
  const ref = useRef<HTMLDListElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const cols = { 1: "sm:grid-cols-1", 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-4" }[
    Math.min(4, Math.max(1, stats.length)) as 1 | 2 | 3 | 4
  ];
  return (
    <dl
      ref={ref}
      className={`divide-border m-0 grid grid-cols-2 divide-y sm:divide-x sm:divide-y-0 ${cols} ${className ?? "max-w-3xl"}`}
    >
      {stats.map((s, i) => (
        <motion.div
          key={s.label}
          className="min-w-0 py-4 sm:px-6 sm:py-1 sm:first:pl-0 sm:last:pr-0"
          initial={{ opacity: 0, y: 10, filter: "blur(6px)" }}
          animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : undefined}
          transition={{ duration: 0.5, delay: i * 0.1, ease: "easeOut" }}
        >
          <dd className="text-foreground m-0 text-3xl font-semibold tracking-tight md:text-4xl">
            {s.revealAfter !== undefined ? (
              <Reveal value={s.value} start={inView} after={s.revealAfter} />
            ) : (
              <Ticker value={s.value} start={inView} tick={s.tick} />
            )}
          </dd>
          <dt className="text-muted-foreground mt-1 text-sm">{s.label}</dt>
        </motion.div>
      ))}
    </dl>
  );
}
