import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronRight as ChevronRightSmall,
  Film,
  LayoutDashboard,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const STORAGE_KEY = "sidebar-collapsed";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

interface NavGroup {
  label: string;
  icon: LucideIcon;
  children: NavItem[];
}

type SidebarItem = NavItem | NavGroup;

function isNavGroup(item: SidebarItem): item is NavGroup {
  return "children" in item;
}

const sidebarItems: SidebarItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  {
    label: "Media",
    icon: Film,
    children: [
      { to: "/media", label: "All Media", icon: Film, end: true },
      { to: "/media/movies", label: "Movies", icon: Film },
      { to: "/media/series", label: "Series", icon: Film },
    ],
  },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  const location = useLocation();
  const [mediaOpen, setMediaOpen] = useState(() =>
    location.pathname.startsWith("/media")
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed));
  }, [collapsed]);

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
      isActive
        ? "text-mt-accent bg-mt-accent/10"
        : "text-mt-light/70 hover:text-mt-light hover:bg-white/5"
    }`;

  return (
    <aside
      className={`flex flex-col bg-[#252422] transition-all duration-200 shrink-0 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      <div className="h-14 flex items-center justify-center px-4 overflow-hidden">
        {collapsed ? (
          <span className="text-mt-accent font-bold text-base tracking-tight">MT</span>
        ) : (
          <span className="text-mt-accent font-semibold text-lg whitespace-nowrap">
            Media Tracker
          </span>
        )}
      </div>

      <nav className="flex-1 flex flex-col gap-1 px-2 py-2">
        {sidebarItems.map((item) => {
          if (isNavGroup(item)) {
            const Icon = item.icon;
            return (
              <div key={item.label}>
                {collapsed ? (
                  <div
                    className="flex items-center justify-center px-3 py-2 rounded-lg text-mt-light/70"
                    title={item.label}
                    aria-label={item.label}
                  >
                    <Icon size={18} className="shrink-0" />
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => setMediaOpen((v) => !v)}
                      className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors text-mt-light/70 hover:text-mt-light hover:bg-white/5"
                    >
                      <Icon size={18} className="shrink-0" />
                      <span className="flex-1 text-left">{item.label}</span>
                      {mediaOpen ? (
                        <ChevronDown size={14} />
                      ) : (
                        <ChevronRightSmall size={14} />
                      )}
                    </button>
                    {mediaOpen && (
                      <div className="flex flex-col gap-1 mt-1 ml-3">
                        {item.children.map((child) => (
                          <NavLink
                            key={child.to}
                            to={child.to}
                            end={child.end}
                            title={child.label}
                            aria-label={child.label}
                            className={navLinkClass}
                          >
                            <span className="w-[18px] shrink-0" />
                            <span>{child.label}</span>
                          </NavLink>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          }

          const { to, label, icon: Icon, end } = item;
          return (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={label}
              aria-label={label}
              className={navLinkClass}
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          );
        })}
      </nav>

      <div className="px-2 pb-4">
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="flex items-center justify-end w-full py-2 pr-1 rounded-lg text-mt-light/70 hover:text-mt-light transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
    </aside>
  );
}
