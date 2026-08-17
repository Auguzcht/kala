import { createRootRoute, Outlet } from "@tanstack/react-router";
import { RootLayout } from "@/app/layout/RootLayout";

export const Route = createRootRoute({
  component: () => (
    <RootLayout>
      <Outlet />
    </RootLayout>
  ),
});
