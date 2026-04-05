import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { HTTPError } from "ky";
import cronstrue from "cronstrue";
import { RefreshCw } from "lucide-react";
import { syncScheduleApi } from "../../api/sync-schedule";
import { syncScheduleSchema } from "./schemas";
import type { SyncScheduleResponse, SyncJobType, SchedulePreset } from "../../types/sync-schedule";

const JOB_LABELS: Record<SyncJobType, string> = {
  jellyfin_users_import: "Jellyfin: Import Users",
  radarr_import: "Radarr: Import Movies",
  jellyfin_import_movies: "Jellyfin: Match Movies",
  jellyfin_movie_watch_history: "Jellyfin: Movie Watch History",
  sonarr_import: "Sonarr: Import Series",
  jellyfin_import_series: "Jellyfin: Match Series",
  jellyfin_series_watch_history: "Jellyfin: Series Watch History",
};

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "2-digit",
  year: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZoneName: "short",
});

interface SyncScheduleFormProps {
  schedule: SyncScheduleResponse;
  hasRunningJobs: boolean;
}

export function SyncScheduleForm({ schedule, hasRunningJobs }: SyncScheduleFormProps) {
  const [preset, setPreset] = useState<SchedulePreset>(schedule.preset);
  const [cronExpression, setCronExpression] = useState(schedule.cron_expression);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [triggerStarted, setTriggerStarted] = useState(false);
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      syncScheduleApi.update(schedule.job_type, {
        preset,
        cron_expression: preset === "custom" ? cronExpression : undefined,
      }),
    onSuccess: () => {
      setErrorMessage(null);
      void queryClient.invalidateQueries({ queryKey: ["sync-schedules"] });
    },
    onError: async (error: unknown) => {
      if (error instanceof HTTPError && error.response.status === 409) {
        try {
          const body = await error.response.json<{ detail?: string; message?: string }>();
          setErrorMessage(body.detail ?? body.message ?? error.message);
        } catch {
          setErrorMessage(error.message);
        }
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("An error occurred");
      }
    },
  });

  const triggerMutation = useMutation({
    mutationFn: () => syncScheduleApi.trigger(schedule.job_type),
    onSuccess: () => {
      setTriggerStarted(true);
      setTimeout(() => setTriggerStarted(false), 2000);
      void queryClient.invalidateQueries({ queryKey: ["sync-schedules"] });
    },
    onError: async (error: unknown) => {
      if (error instanceof HTTPError) {
        try {
          const body = await error.response.json<{ detail?: string; message?: string }>();
          setErrorMessage(body.detail ?? body.message ?? error.message);
        } catch {
          setErrorMessage(error.message);
        }
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("An error occurred");
      }
    },
  });

  const handleSave = () => {
    const parseResult = syncScheduleSchema.safeParse(
      preset === "custom" ? { preset, cron_expression: cronExpression } : { preset }
    );
    if (!parseResult.success) {
      setErrorMessage(parseResult.error.errors[0]?.message ?? "Validation error");
      return;
    }
    setErrorMessage(null);
    mutate();
  };

  const cronDescriptionRaw =
    preset === "custom"
      ? cronstrue.toString(cronExpression, { throwExceptionOnParseError: false })
      : null;
  const cronDescription =
    cronDescriptionRaw && !cronDescriptionRaw.toLowerCase().startsWith("an error")
      ? cronDescriptionRaw
      : null;

  const isDisabled = !schedule.is_enabled;

  const isDirty =
    preset !== schedule.preset ||
    (preset === "custom" && cronExpression !== schedule.cron_expression);

  const runButtonLabel = triggerMutation.isPending
    ? "Starting..."
    : triggerStarted
      ? "Started!"
      : schedule.is_running
        ? "Running..."
        : "Run now";

  return (
    <div className={`border rounded-xl p-4 bg-white/40 flex flex-col items-center transition-colors duration-200 ${isDirty ? "border-mt-accent/60" : "border-[#c9b89a]/30"}`}>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-[#2a2520] font-medium text-sm">{JOB_LABELS[schedule.job_type]}</h3>
        {schedule.is_running && (
          <span role="status" aria-live="polite">
            <RefreshCw size={14} aria-hidden="true" className="text-amber-600 animate-spin" />
            <span className="sr-only">Synchronization in progress</span>
          </span>
        )}
      </div>

      {isDisabled && (
        <p className="text-[#2a2520]/70 text-xs mb-3">Service not configured</p>
      )}

      {/* Preset row */}
      <div className="mb-2">
        <label htmlFor={`${schedule.job_type}-preset`} className="sr-only">
          Schedule preset
        </label>
        <select
          id={`${schedule.job_type}-preset`}
          value={preset}
          disabled={isDisabled}
          onChange={(e) => setPreset(e.target.value as SchedulePreset)}
          className="w-48 bg-white/80 border border-[#c9b89a] rounded-lg px-3 pr-8 py-2 text-sm text-[#2a2520] focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none disabled:opacity-50"
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="custom">Custom</option>
        </select>
      </div>

      {/* Custom cron row */}
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-200 ${preset === "custom" ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}
      >
        <div className="overflow-hidden">
          <div className="mb-2 pt-0.5">
            <label htmlFor={`${schedule.job_type}-cron`} className="sr-only">
              Cron expression
            </label>
            <input
              id={`${schedule.job_type}-cron`}
              type="text"
              value={cronExpression}
              disabled={isDisabled || preset !== "custom"}
              onChange={(e) => setCronExpression(e.target.value)}
              placeholder="* * * * *"
              className="w-48 bg-white/80 border border-[#c9b89a] rounded-lg px-3 py-2 text-sm text-[#2a2520] placeholder-[#2a2520]/50 focus:border-mt-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none disabled:opacity-50"
            />
            <p aria-live="polite" className="text-[#2a2520]/70 text-xs mt-1 h-4">
              {cronDescription ? `${cronDescription} (UTC)` : ""}
            </p>
          </div>
        </div>
      </div>

      {/* Error message */}
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-200 ${errorMessage ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}
      >
        <div className="overflow-hidden">
          <p role="alert" className="text-red-600 text-xs mt-2">
            {errorMessage}
          </p>
        </div>
      </div>

      <div className="mt-auto flex flex-col items-center gap-2 pt-3 w-full">
        {schedule.next_run_at !== null && (
          <p className="text-[#2a2520]/70 text-xs">
            Next: {dateFormatter.format(new Date(schedule.next_run_at))}
          </p>
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={isPending || isDisabled || !isDirty}
          className={`w-48 py-2 rounded-lg font-semibold text-sm transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none disabled:opacity-50 ${isDirty ? "bg-mt-accent text-mt-black hover:bg-mt-accent/90" : "bg-mt-accent/40 text-mt-black/60"}`}
        >
          {isPending ? "Saving..." : isDirty ? "Save changes" : "Saved"}
        </button>
        <button
          type="button"
          aria-label={`Run ${JOB_LABELS[schedule.job_type]} now`}
          aria-busy={schedule.is_running || triggerMutation.isPending}
          onClick={() => triggerMutation.mutate()}
          disabled={!schedule.is_enabled || hasRunningJobs || triggerMutation.isPending}
          className="w-48 py-2 rounded-lg font-semibold text-sm transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none disabled:opacity-60 border border-mt-accent/60 bg-transparent text-[#2a2520] hover:bg-mt-accent/20"
        >
          {runButtonLabel}
        </button>
        <div
          className={`grid transition-[grid-template-rows,opacity] duration-200 ${hasRunningJobs && !schedule.is_running ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}
        >
          <div className="overflow-hidden">
            <p className="text-[#2a2520]/70 text-xs">Another sync is running</p>
          </div>
        </div>
      </div>
    </div>
  );
}
