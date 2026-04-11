import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";
import { AuthGuard } from "./auth/auth-guard";
import { AppLayout } from "./components/layout/app-layout";
import { AuthPage } from "./pages/auth-page";
import { DashboardPage } from "./pages/dashboard-page";
import { ForgotPasswordPage } from "./pages/forgot-password-page";
import { MediaListPage } from "./pages/media-list-page";
import { SettingsPage } from "./pages/settings-page";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

const router = createBrowserRouter([
  {
    path: "/auth",
    element: <AuthPage />,
  },
  {
    path: "/forgot-password",
    element: <ForgotPasswordPage />,
  },
  {
    path: "/",
    element: (
      <AuthGuard>
        <AppLayout breadcrumb={["Dashboard"]}>
          <DashboardPage />
        </AppLayout>
      </AuthGuard>
    ),
  },
  {
    path: "/settings",
    element: (
      <AuthGuard>
        <AppLayout breadcrumb={["Settings"]}>
          <SettingsPage />
        </AppLayout>
      </AuthGuard>
    ),
  },
  {
    path: "/media",
    element: (
      <AuthGuard>
        <AppLayout breadcrumb={["Dashboard", "Media"]}>
          <MediaListPage />
        </AppLayout>
      </AuthGuard>
    ),
  },
  {
    path: "/media/movies",
    element: (
      <AuthGuard>
        <AppLayout breadcrumb={["Dashboard", "Media", "Movies"]}>
          <MediaListPage type="movie" />
        </AppLayout>
      </AuthGuard>
    ),
  },
  {
    path: "/media/series",
    element: (
      <AuthGuard>
        <AppLayout breadcrumb={["Dashboard", "Media", "Series"]}>
          <MediaListPage type="series" />
        </AppLayout>
      </AuthGuard>
    ),
  },
  {
    path: "*",
    element: <Navigate to="/auth" replace />,
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
