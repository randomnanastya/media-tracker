import { useNavigate } from "react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { authApi } from "../api/auth";

export function HomePage() {
  const navigate = useNavigate();

  const { data: user, isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
  });

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      void navigate("/auth", { replace: true });
    },
  });

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <main>
      <h1>Media Tracker</h1>
      <p>Welcome, {user?.username}</p>
      <button
        type="button"
        onClick={handleLogout}
        disabled={logoutMutation.isPending}
        aria-busy={logoutMutation.isPending}
        className="focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none rounded"
      >
        Logout
      </button>
    </main>
  );
}
