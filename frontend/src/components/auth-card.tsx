import type { ReactNode } from "react";
import { Logo } from "./logo";

interface AuthCardProps {
  title: string;
  children: ReactNode;
}

export function AuthCard({ title, children }: AuthCardProps) {
  return (
    <div className="bg-mt-card-bg backdrop-blur-xl border border-mt-card-border rounded-2xl p-8 w-full max-w-sm shadow-2xl">
      <Logo />
      <h1 className="text-mt-light text-xl font-semibold mb-6 text-center">
        {title}
      </h1>
      {children}
    </div>
  );
}
