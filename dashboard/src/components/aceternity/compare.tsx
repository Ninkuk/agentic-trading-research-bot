// Aceternity UI "Compare" (MIT), adapted: the two layers are arbitrary
// content, not images, stacked in one grid cell so the box takes the
// taller one's height; the sparkles layer (a tsparticles dependency) is
// dropped; the divider glows in the theme's primary; autoplay is one
// eased path through given waypoints once the box scrolls into view (not
// the original endless ping-pong), after which the divider rests at the
// last waypoint and moves only under the pointer. Off under reduced
// motion. https://ui.aceternity.com/components/compare

import { GripVertical } from "lucide-react";
import { useInView, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "../ui/utils";

interface CompareProps {
  /** Shown on the left of the divider, wiped away as it moves left. */
  first: ReactNode;
  /** Shown on the right of the divider. */
  second: ReactNode;
  className?: string;
  /** Where the divider starts and, in hover mode, returns to. */
  initialSliderPercentage?: number;
  /** hover: the divider follows the pointer; drag: it moves while held. */
  slideMode?: "hover" | "drag";
  /** Wipe once from `initialSliderPercentage` through these waypoints. */
  autoplay?: boolean;
  /** Waypoints of that pass; the divider rests at the last. */
  autoplayPath?: number[];
  /** Time for a full-width wipe, in ms; shorter legs take their share. */
  autoplayDuration?: number;
}

/** Smootherstep: the wipe lingers on each full view and crosses quickly,
 * so two half-sentences share the box as briefly as possible. */
function ease(t: number): number {
  return t * t * t * (t * (t * 6 - 15) + 10);
}

export function Compare({
  first,
  second,
  className,
  initialSliderPercentage = 50,
  slideMode = "hover",
  autoplay = false,
  autoplayPath = [100 - initialSliderPercentage],
  autoplayDuration = 4000,
}: CompareProps) {
  const restAt = autoplayPath[autoplayPath.length - 1] ?? initialSliderPercentage;
  const [percent, setPercent] = useState(initialSliderPercentage);
  // Where the divider sits when the pointer leaves: the start until the
  // pass has run, the path's end after.
  const [rest, setRest] = useState(initialSliderPercentage);
  const [dragging, setDragging] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const frame = useRef<number | null>(null);
  const played = useRef(false);
  const reduce = useReducedMotion();
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const play = autoplay && inView && !reduce;

  const stop = useCallback(() => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = null;
  }, []);

  useEffect(() => {
    if (!play || played.current) return;
    played.current = true;
    const legs: { from: number; to: number; start: number; ms: number }[] = [];
    let from = initialSliderPercentage;
    let start = 0;
    for (const to of autoplayPath) {
      const ms = (autoplayDuration * Math.abs(to - from)) / 100;
      legs.push({ from, to, start, ms });
      from = to;
      start += ms;
    }
    const t0 = performance.now();
    const tick = (now: number) => {
      const elapsed = now - t0;
      const leg = legs.find((l) => elapsed < l.start + l.ms);
      if (!leg) {
        frame.current = null;
        setPercent(restAt);
        setRest(restAt);
        return;
      }
      setPercent(leg.from + (leg.to - leg.from) * ease((elapsed - leg.start) / leg.ms));
      frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return stop;
  }, [play, initialSliderPercentage, autoplayPath, autoplayDuration, restAt, stop]);

  const moveTo = useCallback((clientX: number) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return;
    setPercent(Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100)));
  }, []);

  const onMouseMove = (e: React.MouseEvent) => {
    if (slideMode === "hover" || dragging) moveTo(e.clientX);
  };
  const onMouseLeave = () => {
    setDragging(false);
    if (slideMode === "hover") setPercent(rest);
  };
  const onTouchMove = (e: React.TouchEvent) => {
    if (dragging) moveTo(e.touches[0].clientX);
  };

  return (
    <div
      ref={ref}
      className={cn("relative grid overflow-hidden select-none", className)}
      style={{ cursor: slideMode === "drag" ? (dragging ? "grabbing" : "grab") : "col-resize" }}
      onMouseEnter={() => {
        stop();
        setRest(restAt);
      }}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      onMouseDown={() => setDragging(true)}
      onMouseUp={() => setDragging(false)}
      onTouchStart={(e) => {
        stop();
        setDragging(true);
        moveTo(e.touches[0].clientX);
      }}
      onTouchMove={onTouchMove}
      onTouchEnd={() => setDragging(false)}
    >
      <div className="[grid-area:1/1]">{second}</div>
      <div className="[grid-area:1/1]" style={{ clipPath: `inset(0 ${100 - percent}% 0 0)` }}>
        {first}
      </div>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 z-10 w-px"
        style={{ left: `${percent}%` }}
      >
        <div className="from-primary/0 via-primary to-primary/0 absolute inset-0 bg-gradient-to-b" />
        <div className="from-primary/40 absolute top-0 bottom-0 left-0 w-24 bg-gradient-to-r to-transparent opacity-60 [mask-image:radial-gradient(90px_at_left,white,transparent)]" />
        <div className="bg-background border-border absolute top-1/2 left-1/2 flex size-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-md border shadow-sm">
          <GripVertical className="text-foreground size-4" />
        </div>
      </div>
    </div>
  );
}
