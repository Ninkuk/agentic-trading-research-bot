// The app shell around both routes: shadcn Sidebar (Summary + one item
// per strand) on the left, masthead + route content in the inset. The
// active item follows the hash route; a bare section or group anchor
// lights the strand that holds it. Each strand is a collapsible holding
// its sub-items (publishers for Sources, live sections elsewhere), the
// chevron toggling it; arriving on a strand opens it, and scroll-spy
// marks the sub-item in view. The open set is session state, never a
// pref: a persisted set drifts from where the reader is.
// Open/closed state of the rail lives in prefs so a reader who collapses
// it finds it collapsed tomorrow; the mobile sheet closes itself on
// navigation.

import { useEffect, useState, type ReactNode } from "react";
import {
  Briefcase,
  ChartLine,
  ChevronRight,
  Database,
  Ellipsis,
  FlaskConical,
  Globe,
  House,
  Radio,
  Wrench,
} from "lucide-react";
import type { HashRoute } from "../hooks/useHashRoute";
import { usePrefs } from "../hooks/usePrefs";
import { useScrollSpy } from "../hooks/useScrollSpy";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../components/ui/collapsible";
import {
  strandId,
  strandItems,
  strandLabels,
  strandOfAnchor,
  strandOfSection,
  strandSections,
  type StrandLabel,
  type SubItem,
} from "../strands";
import type { DashboardDoc } from "../types";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarInset,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "../components/ui/sidebar";
import { useSidebar } from "../components/ui/sidebarContext";
import { Masthead } from "./Masthead";

const STRAND_ICONS: Record<StrandLabel, typeof Globe> = {
  Macro: Globe,
  Signals: Radio,
  Sources: Database,
  Research: FlaskConical,
  "Track record": ChartLine,
  "Your book": Briefcase,
  Ops: Wrench,
  Other: Ellipsis,
};

/** Sidebar slug the route points at: "summary" on the home page, a strand
 * slug on strand/section routes, null on the ticker drill-down. */
function activeSlug(
  route: HashRoute,
  doc: DashboardDoc,
  labels: StrandLabel[],
): string | null {
  switch (route.route) {
    case "main":
      return "summary";
    case "strand":
      return route.id;
    case "section":
      return (
        strandOfSection(doc.sections, route.id) ??
        strandOfAnchor(labels, route.id)
      );
    case "ticker":
      return null;
  }
}

interface NavItemProps {
  href: string;
  label: string;
  icon: typeof Globe;
  active: boolean;
}

function NavLink({ href, label, icon: Icon, active }: NavItemProps) {
  const { isMobile, setOpenMobile } = useSidebar();
  return (
    <SidebarMenuButton asChild isActive={active}>
      <a
        href={href}
        aria-current={active ? "page" : undefined}
        className="no-underline"
        onClick={() => isMobile && setOpenMobile(false)}
      >
        <Icon />
        <span>{label}</span>
      </a>
    </SidebarMenuButton>
  );
}

function NavItem(props: NavItemProps) {
  return (
    <SidebarMenuItem>
      <NavLink {...props} />
    </SidebarMenuItem>
  );
}

interface StrandItemProps extends NavItemProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: SubItem[];
}

// A strand row: the label navigates, the chevron toggles the sub-items.
function StrandItem({ open, onOpenChange, items, ...link }: StrandItemProps) {
  return (
    <Collapsible
      open={open}
      onOpenChange={onOpenChange}
      className="group/collapsible"
      asChild
    >
      <SidebarMenuItem>
        <NavLink {...link} />
        {items.length > 0 && (
          <>
            <CollapsibleTrigger asChild>
              <SidebarMenuAction
                aria-label={`${open ? "Collapse" : "Expand"} ${link.label}`}
              >
                <ChevronRight className="transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
              </SidebarMenuAction>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <StrandSubMenu items={items} />
            </CollapsibleContent>
          </>
        )}
      </SidebarMenuItem>
    </Collapsible>
  );
}

interface StrandSubMenuProps {
  items: SubItem[];
}

// The expanded strand's table of contents. Long titles truncate (the
// button's last span) with the full title in the tooltip.
function StrandSubMenu({ items }: StrandSubMenuProps) {
  const { isMobile, setOpenMobile } = useSidebar();
  const visible = useScrollSpy(items.flatMap((it) => it.ids));
  const current = visible
    ? (items.find((it) => it.ids.includes(visible))?.anchor ?? null)
    : null;
  return (
    <SidebarMenuSub>
      {items.map((it) => (
        <SidebarMenuSubItem key={it.anchor}>
          <SidebarMenuSubButton asChild isActive={current === it.anchor}>
            <a
              href={`#${it.anchor}`}
              title={it.label}
              aria-current={current === it.anchor ? "location" : undefined}
              className="no-underline"
              onClick={() => isMobile && setOpenMobile(false)}
            >
              <span>{it.label}</span>
            </a>
          </SidebarMenuSubButton>
        </SidebarMenuSubItem>
      ))}
    </SidebarMenuSub>
  );
}

interface AppShellProps {
  doc: DashboardDoc;
  route: HashRoute;
  children: ReactNode;
}

export function AppShell({ doc, route, children }: AppShellProps) {
  const [open, setOpen] = usePrefs("sidebar-open", true);
  const labels = strandLabels(doc.sections);
  const active = activeSlug(route, doc, labels);
  // Strands the reader has open. Landing on a strand opens it; the
  // chevron closes or opens any strand for the rest of the session.
  const [opened, setOpened] = useState<Set<string>>(
    () => new Set(active ? [active] : []),
  );
  useEffect(() => {
    if (active)
      setOpened((prev) =>
        prev.has(active) ? prev : new Set(prev).add(active),
      );
  }, [active]);
  function setStrandOpen(slug: string, open: boolean): void {
    setOpened((prev) => {
      const next = new Set(prev);
      if (open) next.add(slug);
      else next.delete(slug);
      return next;
    });
  }

  return (
    <SidebarProvider open={open} onOpenChange={setOpen}>
      <Sidebar>
        <SidebarContent>
          <nav aria-label="sections" className="contents">
            <SidebarGroup>
              <SidebarGroupLabel>Tonight</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <NavItem
                    href="#/"
                    label="Summary"
                    icon={House}
                    active={active === "summary"}
                  />
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
            <SidebarGroup>
              <SidebarGroupLabel>Sections</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {labels.map((label) => {
                    const slug = strandId(label);
                    return (
                      <StrandItem
                        key={label}
                        href={`#/${slug}`}
                        label={label}
                        icon={STRAND_ICONS[label]}
                        active={active === slug}
                        open={opened.has(slug)}
                        onOpenChange={(open) => setStrandOpen(slug, open)}
                        items={strandItems(
                          slug,
                          strandSections(doc.sections, label),
                        )}
                      />
                    );
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </nav>
        </SidebarContent>
        <SidebarRail />
      </Sidebar>
      {/* min-w-0: the inset is a flex item, so without it its min-content
          width is the widest table's and a tablet gets a page-wide
          horizontal scroll instead of per-table scrolling. */}
      <SidebarInset className="min-w-0">
        <div className="page">
          <Masthead
            editionDate={doc.edition_date}
            snapshotNumber={doc.snapshot_number}
            leading={<SidebarTrigger className="-ml-1" />}
          />
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
