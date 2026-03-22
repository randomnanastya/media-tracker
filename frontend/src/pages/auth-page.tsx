import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AuthCard } from "../components/auth-card";
import { LoginForm } from "../features/auth/login-form";
import { RegisterForm } from "../features/auth/register-form";
import { RecoveryCodeDisplay } from "../features/auth/recovery-code-display";
import { authApi } from "../api/auth";

type AuthMode = "login" | "register";

export function AuthPage() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [recoveryCode, setRecoveryCode] = useState<string | null>(null);
  const { data: status } = useQuery({
    queryKey: ["auth-status"],
    queryFn: authApi.getStatus,
  });

  if (recoveryCode) {
    return (
      <AuthLayout>
        <AuthCard title="Save your recovery code">
          <RecoveryCodeDisplay
            code={recoveryCode}
            onContinue={() => {
              setRecoveryCode(null);
              setMode("login");
            }}
          />
        </AuthCard>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <AuthCard title={mode === "login" ? "Sign in to continue" : "Create account"}>
        {mode === "login" ? (
          <LoginForm onSwitchToRegister={status?.setup_required ? () => setMode("register") : undefined} />
        ) : (
          <RegisterForm
            onSuccess={(code) => setRecoveryCode(code)}
            onSwitchToLogin={() => setMode("login")}
          />
        )}
      </AuthCard>
    </AuthLayout>
  );
}

function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main
      className="min-h-screen flex items-center justify-center bg-cover bg-center"
      style={{ backgroundImage: "url('/background_auth.jpg')" }}
    >
      <div className="absolute inset-0 backdrop-blur-sm bg-black/30" />
      <div className="relative z-10">{children}</div>
    </main>
  );
}
