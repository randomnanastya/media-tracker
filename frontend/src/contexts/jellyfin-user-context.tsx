import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { usersApi } from "../api/users";
import type { JellyfinUser } from "../types/user";

interface JellyfinUserContextValue {
  users: JellyfinUser[];
  selectedUser: JellyfinUser | null;
  setSelectedUser: (user: JellyfinUser) => void;
  isLoading: boolean;
}

const JellyfinUserContext = createContext<JellyfinUserContextValue | null>(null);

export function JellyfinUserProvider({ children }: { children: ReactNode }) {
  const [selectedUser, setSelectedUserState] = useState<JellyfinUser | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["jellyfin-users"],
    queryFn: usersApi.listJellyfinUsers,
  });

  useEffect(() => {
    if (users.length === 0) return;

    if (users.length === 1) {
      setSelectedUserState(users[0]);
      localStorage.setItem("jellyfin_user_id", users[0].jellyfin_user_id ?? "");
      return;
    }

    const savedId = localStorage.getItem("jellyfin_user_id");
    if (savedId) {
      const match = users.find((u) => u.jellyfin_user_id === savedId);
      if (match) setSelectedUserState(match);
    }
  }, [users]);

  function setSelectedUser(user: JellyfinUser) {
    setSelectedUserState(user);
    localStorage.setItem("jellyfin_user_id", user.jellyfin_user_id ?? "");
  }

  return (
    <JellyfinUserContext.Provider value={{ users, selectedUser, setSelectedUser, isLoading }}>
      {children}
    </JellyfinUserContext.Provider>
  );
}

export function useJellyfinUser() {
  const ctx = useContext(JellyfinUserContext);
  if (!ctx) throw new Error("useJellyfinUser must be used within JellyfinUserProvider");
  return ctx;
}
