import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { AuthCard } from "../components/auth-card";
import { ForgotPasswordForm } from "../features/auth/forgot-password-form";
import { RecoveryCodeDisplay } from "../features/auth/recovery-code-display";

export function ForgotPasswordPage() {
  const [newCode, setNewCode] = useState<string | null>(null);
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center"
      style={{ backgroundImage: "url('/background_auth.jpg')" }}
    >
      <div className="absolute inset-0 backdrop-blur-md bg-black/30" />
      <div className="relative z-10">
        <AuthCard title="Reset password">
          {newCode === null ? (
            <>
              <ForgotPasswordForm onSuccess={(code) => setNewCode(code)} />
              <Link
                to="/auth"
                className="text-mt-accent text-sm mt-4 block text-center hover:underline"
              >
                Back to sign in
              </Link>
            </>
          ) : (
            <RecoveryCodeDisplay
              code={newCode}
              onContinue={() => void navigate("/auth", { replace: true })}
            />
          )}
        </AuthCard>
      </div>
    </div>
  );
}
