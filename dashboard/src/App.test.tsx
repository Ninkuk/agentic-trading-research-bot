import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "./fixtures/data.json";
import App from "./App";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

test("renders the main page once the fixture doc loads", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => fixture }));
  render(<App />);
  await waitFor(() => expect(screen.getByText(/Risk-on: leaning into risky assets/)).toBeInTheDocument());
});

test("a fetch failure shows the full-page generation-failed banner", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
  render(<App />);
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(screen.getByRole("alert")).toHaveTextContent("network down");
});

test("a top-level error document shows the generation-failed banner with its generated_at", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        schema_version: 1,
        generated_at: "2026-07-28T04:00:00+00:00",
        error: "generation failed (TypeError)",
      }),
    }),
  );
  render(<App />);
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(screen.getByRole("alert")).toHaveTextContent("generation failed (TypeError)");
  expect(screen.getByRole("alert")).toHaveTextContent("Jul 28");
});

test("a stale document renders normally with a dismissable banner", async () => {
  const staleDoc = { ...fixture, generated_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString() };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => staleDoc }));
  render(<App />);
  // The loading spinner is also a status region, so wait for the banner text.
  await screen.findByText(/this edition is stale/i);
  await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(screen.getByText(/Risk-on: leaning into risky assets/)).toBeInTheDocument();
});

test("the ticker hash route renders the drill-down for a known symbol", async () => {
  location.hash = "#/ticker/AAPL";
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => fixture }));
  render(<App />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument());
});

test("the ticker hash route shows an honest message for a symbol with no exported detail", async () => {
  location.hash = "#/ticker/DECK";
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => fixture }));
  render(<App />);
  await waitFor(() => expect(screen.getByText(/no detail exported for DECK/i)).toBeInTheDocument());
});
