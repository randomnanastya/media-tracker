import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Navigate, Outlet, RouterProvider } from "react-router";
import { AuthGuard } from "./auth/auth-guard";
import { BreadcrumbProvider } from "./contexts/breadcrumb-context";
import { JellyfinUserProvider } from "./contexts/jellyfin-user-context";
import { AppLayout } from "./components/layout/app-layout";
import { AuthPage } from "./pages/auth-page";
import { DashboardPage } from "./pages/dashboard-page";
import { ForgotPasswordPage } from "./pages/forgot-password-page";
import { MediaDetailPage } from "./pages/media-detail-page";
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
    element: (
      <AuthGuard>
        <JellyfinUserProvider>
          <Outlet />
        </JellyfinUserProvider>
      </AuthGuard>
    ),
    children: [
      {
        path: "/",
        element: (
          <AppLayout breadcrumb={["Dashboard"]}>
            <DashboardPage />
          </AppLayout>
        ),
      },
      {
        path: "/settings",
        element: (
          <AppLayout breadcrumb={["Settings"]}>
            <SettingsPage />
          </AppLayout>
        ),
      },
      {
        path: "/media",
        element: (
          <AppLayout breadcrumb={["Dashboard", "Media"]}>
            <MediaListPage />
          </AppLayout>
        ),
      },
      {
        path: "/media/movies",
        element: (
          <AppLayout breadcrumb={["Dashboard", "Media", "Movies"]}>
            <MediaListPage type="movie" />
          </AppLayout>
        ),
      },
      {
        path: "/media/series",
        element: (
          <AppLayout breadcrumb={["Dashboard", "Media", "Series"]}>
            <MediaListPage type="series" />
          </AppLayout>
        ),
      },
      {
        path: "/media/:id",
        element: (
          <AppLayout breadcrumb={["Dashboard", "Media", "Detail"]}>
            <MediaDetailPage />
          </AppLayout>
        ),
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/auth" replace />,
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BreadcrumbProvider>
        <RouterProvider router={router} />
      </BreadcrumbProvider>
    </QueryClientProvider>
  );
}
