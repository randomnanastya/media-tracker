import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

interface BreadcrumbContextValue {
  dynamicCrumb: string | null;
  setDynamicCrumb: (value: string | null) => void;
}

const BreadcrumbContext = createContext<BreadcrumbContextValue | null>(null);

export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [dynamicCrumb, setDynamicCrumb] = useState<string | null>(null);
  return (
    <BreadcrumbContext.Provider value={{ dynamicCrumb, setDynamicCrumb }}>
      {children}
    </BreadcrumbContext.Provider>
  );
}

export function useDynamicCrumb() {
  const ctx = useContext(BreadcrumbContext);
  if (!ctx) throw new Error("useDynamicCrumb must be used within BreadcrumbProvider");
  return ctx;
}
