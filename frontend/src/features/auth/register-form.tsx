import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "../../api/auth";
import { parseAuthError, AUTH_ERROR_MESSAGES } from "../../api/client";
import { InputField } from "../../components/input-field";
import { PasswordField } from "../../components/password-field";
import { SubmitButton } from "../../components/submit-button";
import { registerSchema, type RegisterFormData } from "./schemas";
import userIcon from "../../assets/icons/user.png";

interface RegisterFormProps {
  onSuccess: (recoveryCode: string) => void;
  onSwitchToLogin?: () => void;
}

export function RegisterForm({ onSuccess, onSwitchToLogin }: RegisterFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const mutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: (data) => {
      onSuccess(data.recovery_code);
    },
    onError: async (error) => {
      const body = await parseAuthError(error);
      const code = body?.detail?.code;
      if (code === "AUTH_REGISTRATION_CLOSED") {
        setError("root", {
          message: AUTH_ERROR_MESSAGES["AUTH_REGISTRATION_CLOSED"],
        });
      } else if (code === "AUTH_USERNAME_TAKEN") {
        setError("username", {
          message: AUTH_ERROR_MESSAGES["AUTH_USERNAME_TAKEN"],
        });
      } else {
        setError("root", { message: "Something went wrong. Try again." });
      }
    },
  });

  return (
    <form
      onSubmit={handleSubmit((data) => {
        const payload = { ...data, email: data.email || undefined };
        mutation.mutate(payload);
      })}
    >
      <InputField
        label="Username"
        icon={userIcon}
        placeholder="Username"
        registration={register("username")}
        error={errors.username?.message}
      />
      <PasswordField
        label="Password"
        placeholder="Password"
        registration={register("password")}
        error={errors.password?.message}
      />
      <InputField
        label="Email (optional)"
        icon={userIcon}
        type="email"
        placeholder="email@example.com"
        registration={register("email")}
        error={errors.email?.message}
      />
      {errors.root && (
        <p role="alert" className="text-red-400 text-sm mt-1">{errors.root.message}</p>
      )}
      <SubmitButton label="Create account" isLoading={mutation.isPending} />
      {onSwitchToLogin && (
        <p className="text-mt-light text-sm mt-3 text-center">
          Already have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="text-mt-accent hover:underline cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none rounded"
          >
            Sign in
          </button>
        </p>
      )}
    </form>
  );
}
