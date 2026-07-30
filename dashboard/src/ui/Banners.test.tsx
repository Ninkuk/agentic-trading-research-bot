import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GenerationFailedBanner, StaleBanner } from "./Banners";

test("shows the failure message and, when present, generated_at", () => {
  render(<GenerationFailedBanner message="generation failed (TypeError)" generatedAt="2026-07-28T04:00:00+00:00" />);
  expect(screen.getByRole("alert")).toHaveTextContent("generation failed (TypeError)");
  expect(screen.getByRole("alert")).toHaveTextContent("Jul 28");
});

test("omits the attempt time when generatedAt is absent", () => {
  render(<GenerationFailedBanner message="network down" />);
  expect(screen.getByRole("alert")).toHaveTextContent("network down");
  expect(screen.getByRole("alert")).not.toHaveTextContent("last attempt");
});

test("stale banner calls onDismiss when clicked", async () => {
  const onDismiss = vi.fn();
  render(<StaleBanner generatedAt="2026-07-27T00:00:00+00:00" onDismiss={onDismiss} />);
  expect(screen.getByRole("status")).toHaveTextContent("stale");
  await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));
  expect(onDismiss).toHaveBeenCalledTimes(1);
});
