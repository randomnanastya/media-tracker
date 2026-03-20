import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "../../api/auth";
import { parseAuthError, AUTH_ERROR_MESSAGES } from "../../api/client";
import { InputField } from "../../components/input-field";
import { PasswordField } from "../../components/password-field";
import { SubmitButton } from "../../components/submit-button";
import { forgotPasswordSchema, type ForgotPasswordFormData } from "./schemas";
import padlockIcon from "../../assets/icons/padlock.png";

interface ForgotPasswordFormProps {
  onSuccess: (newRecoveryCode: string) => void;
}

export function ForgotPasswordForm({ onSuccess }: ForgotPasswordFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const mutation = useMutation({
    mutationFn: authApi.resetPassword,
    onSuccess: (data) => {
      onSuccess(data.new_recovery_code);
    },
    onError: async (error) => {
      const body = await parseAuthError(error);
      const code = body?.detail?.code;
      if (code === "AUTH_INVALID_RECOVERY_CODE") {
        setError("recovery_code", {
          message: AUTH_ERROR_MESSAGES["AUTH_INVALID_RECOVERY_CODE"],
        });
      } else {
        setError("root", { message: "Something went wrong. Try again." });
      }
    },
  });

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))}>
      <InputField
        label="Recovery code"
        icon={padlockIcon}
        placeholder="Enter your recovery code"
        registration={register("recovery_code")}
        error={errors.recovery_code?.message}
      />
      <PasswordField
        label="New password"
        placeholder="New password"
        registration={register("new_password")}
        error={errors.new_password?.message}
      />
      {errors.root && (
        <p role="alert" className="text-red-400 text-sm mt-1">{errors.root.message}</p>
      )}
      <SubmitButton label="Reset password" isLoading={mutation.isPending} />
    </form>
  );
}
