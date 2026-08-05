import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AboutDialog } from "./AboutDialog";

const ABOUT = [
  { heading: "What this is", body: "Microstructure signals only." },
  { heading: "How much to trust it", body: "Most flags deserve rejection." },
];

test("renders nothing when there are no about blocks", () => {
  const { container } = render(<AboutDialog title="Ticker scorecard" />);
  expect(container).toBeEmptyDOMElement();
  const empty = render(<AboutDialog title="Ticker scorecard" about={[]} />);
  expect(empty.container).toBeEmptyDOMElement();
});

test("clicking the info trigger opens the modal with headed blocks", async () => {
  const user = userEvent.setup();
  render(<AboutDialog title="Ticker scorecard" about={ABOUT} />);

  // Closed by default: only the trigger is on the page.
  expect(screen.queryByText("Microstructure signals only.")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "About Ticker scorecard" }));

  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Ticker scorecard" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "What this is" })).toBeInTheDocument();
  expect(screen.getByText("Most flags deserve rejection.")).toBeInTheDocument();
});

test("escape closes the modal", async () => {
  const user = userEvent.setup();
  render(<AboutDialog title="Ticker scorecard" about={ABOUT} />);
  await user.click(screen.getByRole("button", { name: "About Ticker scorecard" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
