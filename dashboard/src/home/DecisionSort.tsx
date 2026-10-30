// The morning's sort: the night's write-ups sit in a deck and are dealt,
// one every third of a second once the row scrolls into view, onto a
// pass pile or a buy pile, with each pile's running total beneath. The
// totals start at the calls outside the deck and end at the real ones, so
// the short buy pile is the argument. Own implementation on motion.
// Under reduced motion the dealt state renders at once.

import { motion, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import type { DeckCard } from "./homeFacts";

const DEAL_MS = 320;
const TICKET_H = 34;
const PILE_TOP = 64;
const PILE_STEP = 6;
const PILE_X = { pass: "25%", buy: "75%" } as const;

/** A fixed, scattered-looking lie for each ticket on its pile. */
function tilt(i: number): number {
  return ((i * 7919) % 11) - 5;
}

export function DecisionSort({
  deck,
  totals,
  className,
}: {
  deck: DeckCard[];
  totals: { passes: number; buys: number };
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const reduce = useReducedMotion();
  const [dealt, setDealt] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setDealt(deck.length);
      return;
    }
    const id = setInterval(() => {
      setDealt((n) => {
        if (n + 1 >= deck.length) clearInterval(id);
        return Math.min(deck.length, n + 1);
      });
    }, DEAL_MS);
    return () => clearInterval(id);
  }, [inView, reduce, deck.length]);

  const inDeck = { pass: 0, buy: 0 };
  for (const c of deck) inDeck[c.call] += 1;
  const landed = { pass: 0, buy: 0 };
  const pileIndex: number[] = [];
  for (let i = 0; i < deck.length; i++) {
    pileIndex.push(landed[deck[i].call]);
    if (i < dealt) landed[deck[i].call] += 1;
  }
  const shown = {
    pass: totals.passes - inDeck.pass + landed.pass,
    buy: totals.buys - inDeck.buy + landed.buy,
  };
  const tallest = Math.max(inDeck.pass, inDeck.buy);
  const height = PILE_TOP + TICKET_H + tallest * PILE_STEP + 56;

  return (
    <div ref={ref} className={className} role="figure" aria-label="the morning's sort: pass pile and buy pile">
      <div className="relative w-full" style={{ height }}>
        {deck.map((c, i) => {
          const done = i < dealt;
          const k = pileIndex[i];
          return (
            <motion.div
              key={`${c.ticker}-${c.date}`}
              // Neutral in the deck, tinted only once it lands on the buy
              // pile. Opaque faces: the tone background is translucent and a
              // stacked pile would show every ticker through the one on top.
              className={`absolute flex items-center gap-2 rounded-md border px-2.5 font-mono text-sm shadow-sm transition-colors duration-300 ${
                done && c.call === "buy"
                  ? "border-tone-up/50 bg-[color-mix(in_srgb,var(--card),var(--tone-up)_14%)] text-tone-up"
                  : "bg-card border-border text-foreground"
              }`}
              style={{ height: TICKET_H - 4, translateX: "-50%", zIndex: done ? k + 1 : deck.length - i }}
              initial={false}
              animate={
                done
                  ? { left: PILE_X[c.call], top: PILE_TOP + k * PILE_STEP, rotate: tilt(i), opacity: 1 }
                  : { left: "50%", top: (deck.length - 1 - i) * 1.5, rotate: 0, opacity: 1 }
              }
              transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 260, damping: 24 }}
            >
              <span
                aria-hidden="true"
                className={`size-1.5 rounded-full transition-colors duration-300 ${done && c.call === "buy" ? "bg-tone-up" : "bg-muted-foreground/60"}`}
              />
              {c.ticker}
            </motion.div>
          );
        })}
        <Pile side="pass" label="pass" count={shown.pass} />
        <Pile side="buy" label="buy" count={shown.buy} tone />
      </div>
    </div>
  );
}

function Pile({ side, label, count, tone }: { side: "pass" | "buy"; label: string; count: number; tone?: boolean }) {
  return (
    <div
      className="absolute bottom-0 flex -translate-x-1/2 flex-col items-center"
      style={{ left: PILE_X[side] }}
    >
      <motion.span
        key={count}
        className={`text-2xl font-semibold tracking-tight tabular-nums ${tone ? "text-tone-up" : "text-foreground"}`}
        initial={{ scale: 1.15 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 500, damping: 20 }}
      >
        {count.toLocaleString("en-US")}
      </motion.span>
      <span className="text-muted-foreground text-sm">{label}</span>
    </div>
  );
}
