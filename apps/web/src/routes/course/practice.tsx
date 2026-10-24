import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { z } from "zod";

// Retain saved per-skill links; the unscoped legacy entry uses Skills.
const practiceSearchSchema = z.object({
  skillId: z.string().optional(),
  setId: z.string().optional(),
});

export const Route = createFileRoute("/course/practice")({
  validateSearch: practiceSearchSchema,
  component: PracticePage,
});

function PracticePage() {
  const { skillId, setId } = Route.useSearch();
  const navigate = useNavigate();
  useEffect(() => {
    if (skillId) {
      void navigate({ to: "/course/skill/$skillId", params: { skillId }, search: { tab: "test", setId }, replace: true });
    } else {
      void navigate({ to: "/course/skills", replace: true });
    }
  }, [skillId, setId, navigate]);
  return <LoadingPanel label={skillId ? "Opening tests…" : "Opening skills…"} lines={2} />;
}
