import { render } from "@testing-library/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { remarkCallouts } from "./callouts";

function md(src: string) {
  return render(
    <ReactMarkdown remarkPlugins={[remarkGfm, remarkCallouts]}>{src}</ReactMarkdown>,
  ).container;
}

test("a GitHub alert blockquote renders as a typed callout with the marker stripped", () => {
  const c = md("> [!IMPORTANT]\n> **In one sentence:** Apple is great, but pass.");
  const aside = c.querySelector("aside.callout.callout-important");
  expect(aside).toBeInTheDocument();
  expect(aside).toHaveAttribute("data-callout", "important");
  expect(aside?.querySelector(".callout-title")).toHaveTextContent("Important");
  expect(aside).toHaveTextContent("In one sentence: Apple is great, but pass.");
  expect(c.textContent).not.toContain("[!IMPORTANT]");
  expect(c.querySelector("blockquote")).not.toBeInTheDocument();
});

test("all five GitHub alert types are recognised, case-insensitively", () => {
  for (const t of ["note", "tip", "important", "warning", "caution"]) {
    const c = md(`> [!${t.toUpperCase()}]\n> body`);
    expect(c.querySelector(`aside.callout-${t}`), t).toBeInTheDocument();
    const lower = md(`> [!${t}]\n> body`);
    expect(lower.querySelector(`aside.callout-${t}`), `${t} lower`).toBeInTheDocument();
  }
});

test("a callout keeps every block inside the quote, including a list after the lead paragraph", () => {
  const c = md("> [!NOTE]\n> **Reopen trigger:** 2026-11-04:\n> - first\n> - second");
  const aside = c.querySelector("aside.callout-note");
  expect(aside?.querySelectorAll("li")).toHaveLength(2);
  expect(aside).toHaveTextContent("Reopen trigger: 2026-11-04:");
});

test("a plain blockquote is left alone", () => {
  const c = md("> just a quote");
  expect(c.querySelector("blockquote")).toBeInTheDocument();
  expect(c.querySelector("aside")).not.toBeInTheDocument();
});

test("a marker that is not alone on its first line is not an alert (GitHub's rule)", () => {
  const c = md("> [!NOTE] inline text\n> more");
  expect(c.querySelector("blockquote")).toBeInTheDocument();
  expect(c.querySelector("aside")).not.toBeInTheDocument();
  expect(c.textContent).toContain("[!NOTE] inline text");
});

test("an unknown bracket tag is not an alert", () => {
  const c = md("> [!SHOUT]\n> body");
  expect(c.querySelector("blockquote")).toBeInTheDocument();
  expect(c.textContent).toContain("[!SHOUT]");
});
