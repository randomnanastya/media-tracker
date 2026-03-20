import { z } from "zod";

export const changePasswordSchema = z.object({
  current_password: z.string().min(1, "Required"),
  new_password: z.string().min(8, "Min 8 characters").max(128),
  confirm_new_password: z.string().min(1, "Required"),
}).refine((data) => data.new_password === data.confirm_new_password, {
  message: "Passwords do not match",
  path: ["confirm_new_password"],
});

export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;
