import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <p className="text-sm font-medium tracking-wide text-brand-slate">Kala</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight text-foreground">
        Scaffold ready
      </h1>
      <p className="mt-4 text-muted-foreground">
        This page isn't meant to be visited directly, real launches land on{" "}
        <code>/launch</code>. Read <code>CLAUDE.md</code> at the repo root, then build
        features from <code>src/features/_TEMPLATE</code>.
      </p>
    </div>
  );
}
