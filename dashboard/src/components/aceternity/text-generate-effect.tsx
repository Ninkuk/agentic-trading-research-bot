// Aceternity UI "Text Generate Effect" (MIT), adapted: theme tokens instead
// of black/white, no outer margins, a start delay and word stagger prop.
// https://ui.aceternity.com/components/text-generate-effect
import { useEffect } from "react";
import { motion, stagger, useAnimate } from "motion/react";
import { cn } from "../ui/utils";

export const TextGenerateEffect = ({
  words,
  className,
  filter = true,
  duration = 0.5,
  delay = 0,
  stagger: step = 0.2,
}: {
  words: string;
  className?: string;
  filter?: boolean;
  duration?: number;
  /** Seconds before the first word starts, so stacked lines can take turns. */
  delay?: number;
  /** Seconds between words. */
  stagger?: number;
}) => {
  const [scope, animate] = useAnimate();
  const wordsArray = words.split(" ");
  useEffect(() => {
    animate(
      "span",
      {
        opacity: 1,
        filter: filter ? "blur(0px)" : "none",
      },
      {
        duration: duration ? duration : 1,
        delay: stagger(step, { startDelay: delay }),
      }
    );
  }, [scope, animate, duration, filter, delay, step]);

  const renderWords = () => {
    return (
      <motion.div ref={scope}>
        {wordsArray.map((word, idx) => {
          return (
            <motion.span
              key={word + idx}
              className="opacity-0"
              style={{
                filter: filter ? "blur(10px)" : "none",
              }}
            >
              {word}{" "}
            </motion.span>
          );
        })}
      </motion.div>
    );
  };

  return (
    <div className={cn("text-foreground", className)}>{renderWords()}</div>
  );
};
