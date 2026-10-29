// Aceternity UI "Timeline" (MIT), adapted: the caller owns the heading and
// the page column; entries carry a `when` beside the title; colors are the
// dashboard's tokens and the beam is the primary green. The sticky title
// column and the scroll-driven beam are the original's.
// https://ui.aceternity.com/components/timeline

import { motion, useScroll, useTransform } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "../ui/utils";

export interface TimelineEntry {
  when: string;
  title: string;
  content: ReactNode;
  /** The closing entry: its dot and title take the accent. */
  accent?: boolean;
}

export function Timeline({ data, className }: { data: TimelineEntry[]; className?: string }) {
  const ref = useRef<HTMLOListElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (ref.current) setHeight(ref.current.getBoundingClientRect().height);
  }, [ref]);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 10%", "end 50%"],
  });
  const heightTransform = useTransform(scrollYProgress, [0, 1], [0, height]);
  const opacityTransform = useTransform(scrollYProgress, [0, 0.1], [0, 1]);

  return (
    <div className={cn("w-full", className)} ref={containerRef}>
      <ol ref={ref} className="relative m-0 list-none p-0 pb-16">
        {data.map((item) => (
          <li key={item.title} className="flex justify-start pt-12 md:gap-10 md:pt-32">
            <div className="sticky top-28 z-20 flex max-w-xs flex-col items-center self-start md:w-full md:flex-row lg:max-w-sm">
              <div className="bg-background absolute left-3 flex size-10 items-center justify-center rounded-full">
                <div
                  className={cn(
                    "size-4 rounded-full border-2",
                    item.accent
                      ? "border-primary bg-primary shadow-[0_0_0_4px_var(--tone-up-bg)]"
                      : "border-border bg-muted",
                  )}
                />
              </div>
              <div className="hidden md:block md:pl-20">
                <div className="text-muted-foreground font-mono text-sm">{item.when}</div>
                <h3
                  className={cn(
                    "m-0 text-3xl font-semibold tracking-tight lg:text-4xl",
                    item.accent ? "text-tone-up" : "text-foreground",
                  )}
                >
                  {item.title}
                </h3>
              </div>
            </div>
            <div className="relative w-full min-w-0 pr-0 pl-20 md:pl-4">
              <div className="mb-4 md:hidden">
                <div className="text-muted-foreground font-mono text-sm">{item.when}</div>
                <h3 className={cn("m-0 text-2xl font-semibold tracking-tight", item.accent && "text-tone-up")}>
                  {item.title}
                </h3>
              </div>
              {item.content}
            </div>
          </li>
        ))}
        <div
          aria-hidden="true"
          style={{ height: `${height}px` }}
          className="from-border/0 via-border to-border/0 absolute top-0 left-8 w-0.5 overflow-hidden bg-linear-to-b from-0% to-99% [mask-image:linear-gradient(to_bottom,transparent_0%,black_10%,black_90%,transparent_100%)]"
        >
          <motion.div
            style={{ height: heightTransform, opacity: opacityTransform }}
            className="from-primary via-primary absolute inset-x-0 top-0 w-0.5 rounded-full bg-linear-to-t from-0% via-10% to-transparent"
          />
        </div>
      </ol>
    </div>
  );
}
