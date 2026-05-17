import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router";
import logoMark from "../../assets/logo-mark.svg";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Film,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const STORAGE_KEY = "sidebar-collapsed";

function IconFeaturedPlaylist({ size = 18, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M21.75 3.375H2.25C1.85231 3.37545 1.47104 3.53363 1.18983 3.81483C0.908625 4.09604 0.750447 4.47731 0.75 4.875V19.125C0.750447 19.5227 0.908625 19.904 1.18983 20.1852C1.47104 20.4664 1.85231 20.6246 2.25 20.625H21.75C22.1477 20.6246 22.529 20.4664 22.8102 20.1852C23.0914 19.904 23.2496 19.5227 23.25 19.125V4.875C23.2496 4.47731 23.0914 4.09604 22.8102 3.81483C22.529 3.53363 22.1477 3.37545 21.75 3.375ZM21.75 19.125H2.25V4.875H21.75L21.7509 19.125H21.75Z" fill="currentColor"/>
      <path d="M19.5 8.625H10.875V10.125H19.5V8.625Z" fill="currentColor"/>
      <path d="M19.5 12H8.25V13.5H19.5V12Z" fill="currentColor"/>
      <path d="M19.5 15.375H8.25V16.875H19.5V15.375Z" fill="currentColor"/>
      <path d="M4.16815 6.75V12.7933L8.81685 9.5392L4.16815 6.75Z" fill="currentColor"/>
    </svg>
  );
}

function IconMovie({ size = 18, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M6.375 22.875H23.2493V1.125H0.75V22.875H6.375ZM19.125 2.625H21.7493V4.5H19.125V2.625ZM19.125 6H21.7493V7.875H19.125V6ZM19.125 9.375H21.7493V11.25H19.125V9.375ZM19.125 12.75H21.7493V14.625H19.125V12.75ZM19.125 16.125H21.7493V18H19.125V16.125ZM19.125 19.5H21.7493V21.375H19.125V19.5ZM6.375 9.375V2.625H17.6243V11.25H6.375V9.375ZM6.375 19.5V12.75H17.6243V21.375H6.375V19.5ZM2.25 2.625H4.875V4.5H2.25V2.625ZM2.25 6H4.875V7.875H2.25V6ZM2.25 9.375H4.875V11.25H2.25V9.375ZM2.25 12.75H4.875V14.625H2.25V12.75ZM2.25 16.125H4.875V18H2.25V16.125ZM2.25 19.5H4.875V21.375H2.25V19.5Z" fill="currentColor"/>
    </svg>
  );
}

function IconTv({ size = 18, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <g clipPath="url(#clip0_cil_tv)">
        <path d="M22.125 4.14844H14.1856L17.5841 0.75H15.4628L12.0644 4.14844H11.9591L8.56064 0.75H6.43936L9.8378 4.14844H1.875C1.57674 4.14878 1.29079 4.26742 1.07989 4.47833C0.868985 4.68923 0.750347 4.97518 0.75 5.27344V19.1484C0.750347 19.4467 0.868985 19.7326 1.07989 19.9435C1.29079 20.1545 1.57674 20.2731 1.875 20.2734H7.125V23.25H17.625V20.2734H22.125C22.4233 20.2731 22.7092 20.1545 22.9201 19.9435C23.131 19.7326 23.2497 19.4467 23.25 19.1484V5.27344C23.2497 4.97518 23.131 4.68923 22.9201 4.47833C22.7092 4.26742 22.4233 4.14878 22.125 4.14844ZM16.125 21.75H8.625V20.2734H16.125V21.75ZM21.75 18.7734H2.25V5.64844H21.75V18.7734Z" fill="currentColor"/>
      </g>
      <defs>
        <clipPath id="clip0_cil_tv">
          <rect width="24" height="24" fill="white"/>
        </clipPath>
      </defs>
    </svg>
  );
}

type IconComponent = React.ComponentType<{ size?: number; className?: string }>;

interface NavItem {
  to: string;
  label: string;
  icon: IconComponent;
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
      { to: "/media", label: "All Media", icon: IconFeaturedPlaylist, end: true },
      { to: "/media/movies", label: "Movies", icon: IconMovie },
      { to: "/media/series", label: "Series", icon: IconTv },
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
        ? "bg-mt-accent text-[#1a1a1a]"
        : "text-mt-light/90 hover:text-mt-light hover:bg-white/5"
    }`;

  return (
    <aside
      className={`flex flex-col bg-[#252422] transition-all duration-200 shrink-0 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      <NavLink
        to="/"
        className="h-14 flex items-center px-4 overflow-hidden border-b border-white/5 shrink-0"
      >
        {collapsed ? (
          <img src={logoMark} alt="Media Tracker" className="w-8 h-8 mx-auto" />
        ) : (
          <div className="flex items-center gap-2">
            <img src={logoMark} alt="" className="w-7 h-7 shrink-0" />
            <span className="text-mt-accent font-bold text-lg whitespace-nowrap tracking-tight">
              Media Tracker
            </span>
          </div>
        )}
      </NavLink>

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
                      className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors text-mt-light/90 hover:text-mt-light hover:bg-white/5"
                    >
                      <Icon size={18} className="shrink-0" />
                      <span className="flex-1 text-left">{item.label}</span>
                      {mediaOpen ? (
                        <ChevronDown size={14} />
                      ) : (
                        <ChevronRight size={14} />
                      )}
                    </button>
                    {mediaOpen && (
                      <div className="flex flex-col gap-1 mt-1 ml-3 border-l border-white/20 pl-3">
                        {item.children.map((child) => {
                          const ChildIcon = child.icon;
                          return (
                            <NavLink
                              key={child.to}
                              to={child.to}
                              end={child.end}
                              title={child.label}
                              aria-label={child.label}
                              className={navLinkClass}
                            >
                              <ChildIcon size={16} className="shrink-0" />
                              <span>{child.label}</span>
                            </NavLink>
                          );
                        })}
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
          className="flex items-center justify-end w-full py-2 pr-1 rounded-lg text-mt-light/90 hover:text-mt-light transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
    </aside>
  );
}
