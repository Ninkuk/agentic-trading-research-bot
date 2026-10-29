// GitHub-style alerts (`> [!IMPORTANT]` as a blockquote's first line) become
// typed callouts: the mdast blockquote is re-tagged as <aside class="callout
// callout-<type>"> with a title paragraph prepended and the marker stripped.
// The thesis files use these so the same markdown renders as a callout here
// and on GitHub. GitHub's rule: the marker must be alone on the first line.
import type { Blockquote, Paragraph, Parent, Root, Text } from "mdast";

export const CALLOUT_TYPES = ["note", "tip", "important", "warning", "caution"] as const;
export type CalloutType = (typeof CALLOUT_TYPES)[number];

const MARKER = /^\[!(note|tip|important|warning|caution)\](?:\n|$)/i;

function isParent(node: unknown): node is Parent {
  return typeof node === "object" && node !== null && Array.isArray((node as Parent).children);
}

// Returns the alert type when the blockquote's first child is a paragraph whose
// first text node opens with a lone marker line; strips the marker in place.
function claimMarker(quote: Blockquote): CalloutType | null {
  const lead = quote.children[0];
  if (!lead || lead.type !== "paragraph") return null;
  const text = lead.children[0];
  if (!text || text.type !== "text") return null;
  const m = MARKER.exec(text.value);
  if (!m) return null;
  text.value = text.value.slice(m[0].length);
  if (text.value === "") lead.children.shift();
  if (lead.children.length === 0) quote.children.shift();
  return m[1].toLowerCase() as CalloutType;
}

function titleNode(type: CalloutType): Paragraph {
  const label: Text = { type: "text", value: type[0].toUpperCase() + type.slice(1) };
  return {
    type: "paragraph",
    children: [label],
    data: { hProperties: { className: ["callout-title"] } },
  };
}

function walk(node: Parent): void {
  for (const child of node.children) {
    if (child.type === "blockquote") {
      const type = claimMarker(child);
      if (type) {
        child.data = {
          ...child.data,
          hName: "aside",
          hProperties: { className: ["callout", `callout-${type}`], "data-callout": type },
        };
        child.children.unshift(titleNode(type));
      }
    }
    if (isParent(child)) walk(child);
  }
}

export function remarkCallouts() {
  return (tree: Root): void => walk(tree);
}
