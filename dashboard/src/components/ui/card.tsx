import type { ComponentProps } from "react";
import { cn } from "./utils";

export function Card({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card"
      className={cn(
        // No resting shadow (the Floating-Only rule: borders separate
        // surfaces; shadows are reserved for floating layers).
        "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        // From sm, an action slot adds a second column capped at 60% of the
        // header, so a long verdict chip wraps there and never squeezes the
        // title to nothing (the cap is a track max, not a max-width on the
        // action: a percentage max-width is ignored while the track is
        // sized, so the track takes the whole sentence and the chip then
        // wraps inside it with dead space to its right). Below sm the grid
        // stays one implicit column: the action moves under the note
        // (SectionShell), and an explicit two-column template there
        // auto-places the note into column two.
        "grid auto-rows-min items-start gap-1.5 px-6 max-sm:px-4 sm:has-data-[slot=card-action]:grid-cols-[minmax(0,1fr)_minmax(auto,60%)]",
        className,
      )}
      {...props}
    />
  );
}

export function CardTitle({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("leading-none font-semibold", className)}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  );
}

export function CardAction({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn("col-start-2 row-span-2 row-start-1 self-start justify-self-end", className)}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn("px-6 max-sm:px-4", className)} {...props} />;
}

export function CardFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div data-slot="card-footer" className={cn("flex items-center px-6 max-sm:px-4", className)} {...props} />
  );
}
