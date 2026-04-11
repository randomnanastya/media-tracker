import { Fragment } from "react";
import { LogOut } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { authApi } from "../../api/auth";

interface TopBarProps {
  breadcrumb: [string, ...string[]];
}

const BREADCRUMB_PATHS: Record<string, string> = {
  Dashboard: "/",
  Media: "/media",
  Movies: "/media/movies",
  Series: "/media/series",
  Settings: "/settings",
};

export function TopBar({ breadcrumb }: TopBarProps) {
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      void navigate("/auth", { replace: true });
    },
    onError: () => {
      void navigate("/auth", { replace: true });
    },
  });

  return (
    <header className="h-14 flex items-center justify-between px-6 bg-white shadow-sm border-b border-gray-100 shrink-0">
      <div className="flex items-center gap-1.5 text-sm">
        {breadcrumb.map((segment, i) => {
          const isLast = i === breadcrumb.length - 1;
          const path = BREADCRUMB_PATHS[segment];
          return (
            <Fragment key={i}>
              {i > 0 && <span className="text-[#2a2520]/30">›</span>}
              {isLast || !path ? (
                <span className="text-[#2a2520] font-medium">{segment}</span>
              ) : (
                <button
                  type="button"
                  onClick={() => void navigate(path)}
                  className="text-[#2a2520]/50 hover:text-[#2a2520] transition-colors"
                >
                  {segment}
                </button>
              )}
            </Fragment>
          );
        })}
      </div>
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        aria-label="Log out"
        className="text-[#2a2520]/50 hover:text-[#2a2520] transition-colors disabled:opacity-50"
      >
        <LogOut size={18} />
      </button>
    </header>
  );
}
