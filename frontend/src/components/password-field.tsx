import { useState } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";
import padlockIcon from "../assets/icons/padlock.png";
import eyeIcon from "../assets/icons/eye.png";
import eyeClosedIcon from "../assets/icons/eye-closed.png";

interface PasswordFieldProps {
  label: string;
  placeholder?: string;
  error?: string;
  registration: UseFormRegisterReturn;
}

export function PasswordField({
  label,
  placeholder,
  error,
  registration,
}: PasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="mb-4">
      <label htmlFor={registration.name} className="text-mt-light text-sm mb-1 block">
        {label}
      </label>
      <div className="relative">
        <img
          src={padlockIcon}
          alt=""
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 opacity-60"
        />
        <input
          {...registration}
          id={registration.name}
          type={showPassword ? "text" : "password"}
          placeholder={placeholder}
          aria-invalid={!!error}
          aria-describedby={error ? `${registration.name}-error` : undefined}
          className="w-full bg-mt-input-bg border border-mt-input-border rounded-lg pl-10 pr-10 py-2.5 text-mt-light placeholder-mt-light/60 focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
        />
        <button
          type="button"
          onClick={() => setShowPassword((v) => !v)}
          aria-label={showPassword ? "Hide password" : "Show password"}
          className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none rounded"
        >
          <img
            src={showPassword ? eyeIcon : eyeClosedIcon}
            alt=""
            aria-hidden="true"
            className="w-4 h-4 opacity-60"
          />
        </button>
      </div>
      {error && (
        <p id={`${registration.name}-error`} className="text-red-400 text-xs mt-1">
          {error}
        </p>
      )}
    </div>
  );
}
