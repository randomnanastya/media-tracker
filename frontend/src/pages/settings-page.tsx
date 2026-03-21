import { useState } from "react";
import { ChangePasswordForm } from "../features/settings/change-password-form";
import { ExternalServicesSection } from "../features/settings/external-services-form";

type SettingsTab = "account" | "external";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "account", label: "Account Settings" },
  { id: "external", label: "External Services" },
];

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");

  return (
    <div className="p-8">
      <h1 className="text-[#2a2520] text-2xl font-semibold mb-1">Settings</h1>
      <p className="text-[#2a2520]/60 mb-6">Manage your account and integrations</p>

      <div role="tablist" className="flex gap-1 border-b border-[#c9b89a]/50 mb-8">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            type="button"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent ${
              activeTab === tab.id
                ? "border-mt-accent text-[#2a2520]"
                : "border-transparent text-[#2a2520]/50 hover:text-[#2a2520]/80"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "account" && (
        <section
          role="tabpanel"
          id="panel-account"
          aria-labelledby="tab-account"
          tabIndex={0}
          className="max-w-xl focus-visible:outline-none"
        >
          <h2 className="text-[#2a2520] text-lg font-medium mb-4">Change Password</h2>
          <ChangePasswordForm />
        </section>
      )}

      {activeTab === "external" && (
        <section
          role="tabpanel"
          id="panel-external"
          aria-labelledby="tab-external"
          tabIndex={0}
          className="focus-visible:outline-none"
        >
          <ExternalServicesSection />
        </section>
      )}
    </div>
  );
}
