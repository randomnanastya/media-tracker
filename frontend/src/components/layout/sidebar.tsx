import { useEffect, useState } from "react";
import { NavLink } from "react-router";
import { LayoutDashboard, Settings, ChevronLeft, ChevronRight } from "lucide-react";

const STORAGE_KEY = "sidebar-collapsed";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed));
  }, [collapsed]);

  return (
    <aside
      className={`flex flex-col bg-[#252422] transition-all duration-200 shrink-0 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      <div className="h-14 flex items-center px-4 overflow-hidden">
        {!collapsed && (
          <span className="text-mt-accent font-semibold text-lg whitespace-nowrap">
            Media Tracker
          </span>
        )}
      </div>

      <nav className="flex-1 flex flex-col gap-1 px-2 py-2">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "text-mt-accent"
                  : "text-mt-light/70 hover:text-mt-light"
              }`
            }
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
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
