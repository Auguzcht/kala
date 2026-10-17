import type { ReactNode } from "react";
import { SessionBar } from "@/components/study/SessionBar";
import { StudyStream } from "@/components/study/StudyStream";
import { StudySurface } from "@/components/study/StudySurface";

/** Keep the exit available while a session is loading, empty, or unavailable. */
export function SessionState({ title, onExit, children }: {
  title: string;
  onExit: () => void;
  children: ReactNode;
}) {
  return (
    <StudySurface bar={<SessionBar title={title} onBack={onExit} backLabel="Return to menu" />}>
      <StudyStream>{children}</StudyStream>
    </StudySurface>
  );
}
