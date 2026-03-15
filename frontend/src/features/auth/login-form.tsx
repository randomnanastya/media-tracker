import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router";
import { authApi } from "../../api/auth";
import { parseAuthError, AUTH_ERROR_MESSAGES } from "../../api/client";
import { InputField } from "../../components/input-field";
import { PasswordField } from "../../components/password-field";
import { SubmitButton } from "../../components/submit-button";
import { loginSchema, type LoginFormData } from "./schemas";
import userIcon from "../../assets/icons/user.png";

interface LoginFormProps {
  onSwitchToRegister?: () => void;
}

export function LoginForm({ onSwitchToRegister }: LoginFormProps) {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const mutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: () => {
      void navigate("/", { replace: true });
    },
    onError: async (error) => {
      const body = await parseAuthError(error);
      if (body?.detail?.code === "AUTH_INVALID_CREDENTIALS") {
        setError("root", {
          message: AUTH_ERROR_MESSAGES["AUTH_INVALID_CREDENTIALS"],
        });
      } else {
        setError("root", { message: "Something went wrong. Try again." });
      }
    },
  });

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))}>
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
      {errors.root && (
        <p role="alert" className="text-red-400 text-sm mt-1">{errors.root.message}</p>
      )}
      <SubmitButton label="Sign in" isLoading={mutation.isPending} />
      <Link
        to="/forgot-password"
        className="text-mt-accent text-sm mt-4 block text-center hover:underline focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none rounded"
      >
        Forgot password?
      </Link>
      {onSwitchToRegister && (
        <p className="text-mt-light text-sm mt-3 text-center">
          Don&apos;t have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-mt-accent hover:underline cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none rounded"
          >
            Sign up
          </button>
        </p>
      )}
    </form>
  );
}
