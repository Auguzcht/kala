// Router setup. TanStack Router is the chosen router (see docs/stack.md).
// For the scaffold this is a minimal placeholder so the app renders.
// Replace with createRouter + route tree, and register feature routes here.
import { RootLayout } from "@/app/layout/RootLayout";

export function AppRouter() {
  return (
    <RootLayout>
      <div className="mx-auto max-w-2xl px-6 py-16">
        <p className="text-sm font-medium tracking-wide text-brand-teal">
          Kala
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-foreground">
          Scaffold ready
        </h1>
        <p className="mt-4 text-muted-foreground">
          Read <code>CLAUDE.md</code> at the repo root, then build features from{" "}
          <code>src/features/_TEMPLATE</code>. Register routes here.
        </p>
      </div>
    </RootLayout>
  );
}
