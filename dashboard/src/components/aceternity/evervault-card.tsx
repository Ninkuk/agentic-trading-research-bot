// Aceternity UI "evervault-card" (MIT), adapted: only the pattern layer
// (the cursor-following mask over a field of scrambled characters), typed,
// in the primary tone; the demo card, its icon and the string helper (now
// src/home/scramble.ts) are dropped.
// https://ui.aceternity.com/components/evervault-card
import { motion, useMotionTemplate, type MotionValue } from "motion/react";

export function CardPattern({
  mouseX,
  mouseY,
  randomString,
}: {
  mouseX: MotionValue<number>;
  mouseY: MotionValue<number>;
  randomString: string;
}) {
  const maskImage = useMotionTemplate`radial-gradient(250px at ${mouseX}px ${mouseY}px, white, transparent)`;
  const style = { maskImage, WebkitMaskImage: maskImage };
  return (
    <div className="pointer-events-none" aria-hidden="true">
      <motion.div
        className="from-primary to-chart-2 absolute inset-0 rounded-[inherit] bg-linear-to-r opacity-0 backdrop-blur-xl transition duration-500 group-hover/card:opacity-100"
        style={style}
      />
      <motion.div
        className="absolute inset-0 rounded-[inherit] opacity-0 mix-blend-overlay group-hover/card:opacity-100"
        style={style}
      >
        <p className="absolute inset-x-0 m-0 h-full font-mono text-xs font-bold break-words whitespace-pre-wrap text-white transition duration-500">
          {randomString}
        </p>
      </motion.div>
    </div>
  );
}
