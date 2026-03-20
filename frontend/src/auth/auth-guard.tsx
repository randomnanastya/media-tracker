import { useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router";
import { authApi } from "../api/auth";

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [status, setStatus] = useState<"loading" | "ok" | "unauthorized">("loading");

  useEffect(() => {
    authApi.getMe()
      .then(() => setStatus("ok"))
      .catch(() => setStatus("unauthorized"));
  }, []);

  if (status === "loading") return (
    <div className="flex h-screen items-center justify-center bg-[#1a1917]">
      <svg aria-label="Loading" className="animate-spin w-8 h-8 text-mt-accent" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
    </div>
  );
  if (status === "unauthorized") return <Navigate to="/auth" replace />;
  return <>{children}</>;
}
