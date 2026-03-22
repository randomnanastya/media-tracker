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

export const syncScheduleSchema = z.discriminatedUnion("preset", [
  z.object({ preset: z.literal("daily") }),
  z.object({ preset: z.literal("weekly") }),
  z.object({ preset: z.literal("monthly") }),
  z.object({
    preset: z.literal("custom"),
    cron_expression: z.string().min(9, "Invalid cron expression").max(100),
  }),
]);

export type SyncScheduleFormData = z.infer<typeof syncScheduleSchema>;
