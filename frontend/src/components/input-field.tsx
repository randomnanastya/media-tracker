import type { UseFormRegisterReturn } from "react-hook-form";

interface InputFieldProps {
  label: string;
  icon: string;
  type?: string;
  placeholder?: string;
  error?: string;
  registration: UseFormRegisterReturn;
}

export function InputField({
  label,
  icon,
  type = "text",
  placeholder,
  error,
  registration,
}: InputFieldProps) {
  return (
    <div className="mb-4">
      <label htmlFor={registration.name} className="text-mt-light text-sm mb-1 block">
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
          className="w-full bg-mt-input-bg border border-mt-input-border rounded-lg pl-10 pr-3 py-2.5 text-mt-light placeholder-mt-light/60 focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
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
