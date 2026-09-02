// The app shell around both routes: shadcn Sidebar (Summary + one item
// per strand) on the left, masthead + route content in the inset. The
// active item follows the hash route; a bare section anchor lights the
// strand that holds the section. Open/closed state lives in prefs so a
// reader who collapses the rail finds it collapsed tomorrow; the mobile
// sheet closes itself on navigation.

import type { ReactNode } from "react";
import {
  Briefcase,
  ChartLine,
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
import { strandId, strandLabels, strandOfSection, type StrandLabel } from "../strands";
import type { DashboardDoc } from "../types";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
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
function activeSlug(route: HashRoute, doc: DashboardDoc): string | null {
  switch (route.route) {
    case "main":
      return "summary";
    case "strand":
      return route.id;
    case "section":
      return strandOfSection(doc.sections, route.id);
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

function NavItem({ href, label, icon: Icon, active }: NavItemProps) {
  const { isMobile, setOpenMobile } = useSidebar();
  return (
    <SidebarMenuItem>
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
    </SidebarMenuItem>
  );
}

interface AppShellProps {
  doc: DashboardDoc;
  route: HashRoute;
  children: ReactNode;
}

export function AppShell({ doc, route, children }: AppShellProps) {
  const [open, setOpen] = usePrefs("sidebar-open", true);
  const active = activeSlug(route, doc);
  const labels = strandLabels(doc.sections);

  return (
    <SidebarProvider open={open} onOpenChange={setOpen}>
      <Sidebar>
        <SidebarContent>
          <nav aria-label="sections" className="contents">
            <SidebarGroup>
              <SidebarGroupLabel>Tonight</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <NavItem href="#/" label="Summary" icon={House} active={active === "summary"} />
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
                      <NavItem
                        key={label}
                        href={`#/${slug}`}
                        label={label}
                        icon={STRAND_ICONS[label]}
                        active={active === slug}
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
