// Aceternity UI "Compare" (MIT), adapted: the two layers are arbitrary
// content, not images, stacked in one grid cell so the box takes the
// taller one's height; the sparkles layer (a tsparticles dependency) is
// dropped; the divider glows in the theme's primary; autoplay eases and
// dwells at each end instead of a constant sweep, waits for the box to
// scroll into view, and is off under reduced motion. https://ui.aceternity.com/components/compare

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
  autoplay?: boolean;
  /** One end-to-end pass, in ms. */
  autoplayDuration?: number;
}

/** Smootherstep: the sweep dwells on each full view and crosses quickly,
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
  autoplayDuration = 4000,
}: CompareProps) {
  const [percent, setPercent] = useState(initialSliderPercentage);
  const [dragging, setDragging] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const frame = useRef<number | null>(null);
  const reduce = useReducedMotion();
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const play = autoplay && inView && !reduce;

  const stop = useCallback(() => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = null;
  }, []);

  const start = useCallback(() => {
    if (!play) return;
    stop();
    const t0 = performance.now();
    const tick = (now: number) => {
      const progress = ((now - t0) % (autoplayDuration * 2)) / autoplayDuration;
      const p = progress <= 1 ? ease(progress) : ease(2 - progress);
      setPercent(p * 100);
      frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
  }, [play, autoplayDuration, stop]);

  useEffect(() => {
    start();
    return stop;
  }, [start, stop]);

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
    if (slideMode === "hover") setPercent(initialSliderPercentage);
    start();
  };
  const onTouchMove = (e: React.TouchEvent) => {
    if (dragging) moveTo(e.touches[0].clientX);
  };

  return (
    <div
      ref={ref}
      className={cn("relative grid overflow-hidden select-none", className)}
      style={{ cursor: slideMode === "drag" ? (dragging ? "grabbing" : "grab") : "col-resize" }}
      onMouseEnter={stop}
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
      onTouchEnd={() => {
        setDragging(false);
        start();
      }}
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
