import { useJellyfinUser } from "../contexts/jellyfin-user-context";

export function JellyfinUserSelector() {
  const { users, selectedUser, setSelectedUser, isLoading } = useJellyfinUser();

  if (isLoading) {
    return <div className="w-20 h-6 animate-pulse rounded bg-[#c9b89a]/30" />;
  }

  if (users.length <= 1) {
    return null;
  }

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const user = users.find((u) => u.jellyfin_user_id === e.target.value);
    if (user) setSelectedUser(user);
  }

  return (
    <div className="flex items-center gap-2 text-sm text-[#2a2520]/60">
      <label htmlFor="jellyfin-user-select" className="text-sm text-[#2a2520]/60 cursor-pointer">Jellyfin</label>
      <select
        id="jellyfin-user-select"
        value={selectedUser?.jellyfin_user_id ?? ""}
        onChange={handleChange}
        className="text-sm bg-transparent border border-[#c9b89a]/40 rounded-md px-2 py-0.5 text-[#2a2520]"
      >
        <option value="" disabled>
          Select user
        </option>
        {users.map((u) => (
          <option key={u.id} value={u.jellyfin_user_id ?? ""}>
            {u.username}
          </option>
        ))}
      </select>
    </div>
  );
}
