import { ChangePasswordForm } from "../features/settings/change-password-form";

export function SettingsPage() {
  return (
    <div className="p-8">
      <h1 className="text-[#2a2520] text-2xl font-semibold mb-1">Account Settings</h1>
      <p className="text-[#2a2520]/60 mb-8">Manage your account and integrations</p>
      <section>
        <h2 className="text-[#2a2520] text-lg font-medium mb-4">Change Password</h2>
        <ChangePasswordForm />
      </section>
    </div>
  );
}
