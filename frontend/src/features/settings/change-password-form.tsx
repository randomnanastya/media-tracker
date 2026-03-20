import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "../../api/auth";
import { PasswordField } from "../../components/password-field";
import { SubmitButton } from "../../components/submit-button";
import { changePasswordSchema, type ChangePasswordFormData } from "./schemas";

export function ChangePasswordForm() {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
    reset,
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  });

  const mutation = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      reset();
      setSuccessMessage("Password changed successfully");
    },
    onError: () => {
      setError("root", { message: "Current password is incorrect" });
    },
  });

  return (
    <form
      onSubmit={handleSubmit((data) => {
        setSuccessMessage(null);
        const { confirm_new_password, ...payload } = data;
        void confirm_new_password;
        mutation.mutate(payload);
      })}
      className="max-w-sm"
    >
      <PasswordField
        label="Current Password"
        placeholder="Enter current password"
        registration={register("current_password")}
        error={errors.current_password?.message}
        variant="light"
      />
      <PasswordField
        label="New Password"
        placeholder="Enter new password"
        registration={register("new_password")}
        error={errors.new_password?.message}
        variant="light"
      />
      <PasswordField
        label="Confirm New Password"
        placeholder="Repeat new password"
        registration={register("confirm_new_password")}
        error={errors.confirm_new_password?.message}
        variant="light"
      />
      {errors.root && (
        <p role="alert" className="text-red-400 text-sm mt-1">
          {errors.root.message}
        </p>
      )}
      {successMessage && (
        <p role="status" className="text-green-400 text-sm mt-1">
          {successMessage}
        </p>
      )}
      <SubmitButton label="Save Password" isLoading={mutation.isPending} />
    </form>
  );
}
