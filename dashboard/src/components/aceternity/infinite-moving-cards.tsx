// Aceternity UI "infinite-moving-cards" (MIT), adapted: theme tokens, narrower cards, an optional logo per card.
// https://ui.aceternity.com/components/infinite-moving-cards

import { cn } from "../ui/utils";
import React, { useEffect, useState } from "react";

export const InfiniteMovingCards = ({
  items,
  direction = "left",
  speed = "fast",
  durationSeconds,
  pauseOnHover = true,
  className,
}: {
  items: {
    quote: string;
    name: string;
    title: string;
    /** Optional seal/logo beside the name; a card without one shows the name as a wordmark. */
    logo?: string;
  }[];
  direction?: "left" | "right";
  speed?: "fast" | "normal" | "slow";
  /** Overrides `speed` with an exact loop time. */
  durationSeconds?: number;
  pauseOnHover?: boolean;
  className?: string;
}) => {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const scrollerRef = React.useRef<HTMLUListElement>(null);

  useEffect(() => {
    addAnimation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [start, setStart] = useState(false);
  function addAnimation() {
    if (containerRef.current && scrollerRef.current) {
      const scrollerContent = Array.from(scrollerRef.current.children);

      scrollerContent.forEach((item) => {
        const duplicatedItem = item.cloneNode(true);
        if (scrollerRef.current) {
          scrollerRef.current.appendChild(duplicatedItem);
        }
      });

      getDirection();
      getSpeed();
      setStart(true);
    }
  }
  const getDirection = () => {
    if (containerRef.current) {
      if (direction === "left") {
        containerRef.current.style.setProperty(
          "--animation-direction",
          "forwards",
        );
      } else {
        containerRef.current.style.setProperty(
          "--animation-direction",
          "reverse",
        );
      }
    }
  };
  const getSpeed = () => {
    if (containerRef.current) {
      if (durationSeconds) {
        containerRef.current.style.setProperty("--animation-duration", `${durationSeconds}s`);
      } else if (speed === "fast") {
        containerRef.current.style.setProperty("--animation-duration", "20s");
      } else if (speed === "normal") {
        containerRef.current.style.setProperty("--animation-duration", "40s");
      } else {
        containerRef.current.style.setProperty("--animation-duration", "80s");
      }
    }
  };
  return (
    <div
      ref={containerRef}
      className={cn(
        "scroller relative z-20 max-w-7xl overflow-hidden [mask-image:linear-gradient(to_right,transparent,white_20%,white_80%,transparent)]",
        className,
      )}
    >
      <ul
        ref={scrollerRef}
        className={cn(
          "flex w-max min-w-full shrink-0 flex-nowrap gap-4 py-4",
          start && "animate-scroll",
          pauseOnHover && "hover:[animation-play-state:paused]",
        )}
      >
        {items.map((item) => (
          <li
            className="bg-card border-border relative flex w-[300px] max-w-full shrink-0 flex-col rounded-2xl border px-6 py-5 md:w-[380px]"
            key={item.name}
          >
            <blockquote className="m-0 flex h-full flex-col">
              <div
                aria-hidden="true"
                className="user-select-none pointer-events-none absolute -top-0.5 -left-0.5 -z-1 h-[calc(100%_+_4px)] w-[calc(100%_+_4px)]"
              ></div>
              <span className="text-foreground relative z-20 text-sm leading-[1.6] font-normal">
                {item.quote}
              </span>
              <div className="relative z-20 mt-auto flex flex-row items-center gap-3 pt-6">
                {item.logo && (
                  <span className="flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white">
                    <img src={item.logo} alt="" width={40} height={40} loading="lazy" className="size-10 object-cover" />
                  </span>
                )}
                <span className="flex flex-col gap-1">
                  <span className="text-foreground text-sm leading-[1.6] font-medium">
                    {item.name}
                  </span>
                  <span className="text-muted-foreground text-sm leading-[1.6] font-normal">
                    {item.title}
                  </span>
                </span>
              </div>
            </blockquote>
          </li>
        ))}
      </ul>
    </div>
  );
};
