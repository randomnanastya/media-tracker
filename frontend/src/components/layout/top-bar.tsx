import { Fragment } from "react";
import { LogOut } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { authApi } from "../../api/auth";

interface TopBarProps {
  breadcrumb: [string, ...string[]];
}

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
    <header className="h-14 flex items-center justify-between px-6 bg-[#1a1917] border-b border-mt-card-border">
      <div className="flex items-center gap-1.5 text-sm">
        {breadcrumb.map((segment, i) => (
          <Fragment key={i}>
            {i > 0 && <span className="text-mt-light/30">/</span>}
            <span
              className={
                i === breadcrumb.length - 1
                  ? "text-mt-light font-medium"
                  : "text-mt-light/50"
              }
            >
              {segment}
            </span>
          </Fragment>
        ))}
      </div>
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        aria-label="Log out"
        className="text-mt-light/70 hover:text-mt-accent transition-colors disabled:opacity-50"
      >
        <LogOut size={18} />
      </button>
    </header>
  );
}
