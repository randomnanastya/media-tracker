import type { UseFormRegisterReturn } from "react-hook-form";

interface InputFieldProps {
  label: string;
  icon: string;
  type?: string;
  placeholder?: string;
  error?: string;
  registration: UseFormRegisterReturn;
  variant?: "dark" | "light";
}

export function InputField({
  label,
  icon,
  type = "text",
  placeholder,
  error,
  registration,
  variant = "dark",
}: InputFieldProps) {
  const isDark = variant === "dark";
  const labelClass = isDark ? "text-mt-light" : "text-[#2a2520]";
  const inputClass = isDark
    ? "w-full bg-mt-input-bg border border-mt-input-border rounded-lg pl-10 pr-3 py-2.5 text-mt-light placeholder-mt-light/60 focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
    : "w-full bg-white/80 border border-[#c9b89a] rounded-lg pl-10 pr-3 py-2.5 text-[#2a2520] placeholder-[#2a2520]/50 focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none";

  return (
    <div className="mb-4">
      <label htmlFor={registration.name} className={`${labelClass} text-sm mb-1 block`}>
        {label}
      </label>
      <div className="relative">
        <img
          src={icon}
          alt=""
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 opacity-50"
        />
        <input
          {...registration}
          id={registration.name}
          type={type}
          placeholder={placeholder}
          aria-invalid={!!error}
          aria-describedby={error ? `${registration.name}-error` : undefined}
          className={inputClass}
        />
      </div>
      {error && (
        <p id={`${registration.name}-error`} className="text-red-400 text-xs mt-1">
          {error}
        </p>
      )}
    </div>
  );
}
