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

  if (status === "loading") return null;
  if (status === "unauthorized") return <Navigate to="/auth" replace />;
  return <>{children}</>;
}
