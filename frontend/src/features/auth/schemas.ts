import { z } from "zod";

export const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  username: z
    .string()
    .min(3, "Minimum 3 characters")
    .max(100, "Maximum 100 characters"),
  password: z
    .string()
    .min(8, "Minimum 8 characters")
    .max(128, "Maximum 128 characters"),
  email: z
    .string()
    .email("Invalid email")
    .max(255)
    .optional()
    .or(z.literal("")),
});

export type RegisterFormData = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  recovery_code: z.string().min(1, "Recovery code is required"),
  new_password: z
    .string()
    .min(8, "Minimum 8 characters")
    .max(128, "Maximum 128 characters"),
});

export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;
