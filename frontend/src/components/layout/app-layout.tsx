import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";

interface AppLayoutProps {
  breadcrumb: [string, ...string[]];
  children: ReactNode;
}

export function AppLayout({ breadcrumb, children }: AppLayoutProps) {
  return (
    <div className="flex h-screen bg-[#F5ECD7]">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar breadcrumb={breadcrumb} />
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>
    </div>
  );
}
