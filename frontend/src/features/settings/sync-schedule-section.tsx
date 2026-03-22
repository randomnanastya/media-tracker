import { useQuery } from "@tanstack/react-query";
import { syncScheduleApi } from "../../api/sync-schedule";
import { SyncScheduleForm } from "./sync-schedule-form";

export function SyncScheduleSection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["sync-schedules"],
    queryFn: syncScheduleApi.list,
  });

  if (isLoading) return <p className="text-sm text-gray-500">Loading schedules...</p>;
  if (isError || !data) return <p role="alert" className="text-sm text-red-500">Failed to load schedules.</p>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl">
      {data.schedules.map((schedule) => (
        <SyncScheduleForm key={schedule.job_type} schedule={schedule} />
      ))}
    </div>
  );
}
