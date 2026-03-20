import { LogOut } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { authApi } from "../../api/auth";

interface TopBarProps {
  title: string;
}

export function TopBar({ title }: TopBarProps) {
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
      <span className="text-mt-light font-medium">{title}</span>
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
