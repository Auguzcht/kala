import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">
        Kala
      </h1>
      <p className="mt-4 text-muted-foreground">
        Open Kala from your course in Blackboard.
      </p>
    </div>
  );
}
